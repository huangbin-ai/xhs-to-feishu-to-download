#!/usr/bin/env python3
"""
从飞书多维表格读取小红书链接 → 批量下载图片/视频

读取飞书表格中的笔记链接，调用 xhs-downloader 逐条下载。
支持标记已下载状态、断点续传。

配置方式：
  1. 环境变量
  2. 配置文件 ~/.config/xhs-to-feishu/.env

依赖：xhs-downloader（本地已安装）
"""

import json
import os
import sys
import subprocess
import argparse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── 配置加载 ──────────────────────────────────────────

def load_env():
    env_file = os.path.expanduser("~/.config/xhs-to-feishu/.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

load_env()

def require_env(key, desc):
    val = os.environ.get(key, "")
    if not val:
        print(f"❌ 缺少配置：{key}（{desc}）", file=sys.stderr)
        sys.exit(1)
    return val

FEISHU_APP_ID     = require_env("FEISHU_APP_ID", "飞书应用 App ID")
FEISHU_APP_SECRET = require_env("FEISHU_APP_SECRET", "飞书应用 App Secret")
BITABLE_APP_TOKEN = require_env("BITABLE_APP_TOKEN", "飞书多维表格 App Token")
BITABLE_TABLE_ID  = require_env("BITABLE_TABLE_ID", "飞书多维表格 Table ID")

# 下载工具路径
XHS_DOWNLOADER_DIR = os.environ.get(
    "XHS_DOWNLOADER_DIR",
    os.path.expanduser("~/xhs-downloader")
)
XHS_PYTHON = os.environ.get("XHS_PYTHON", "python3")
XHS_COOKIE_FILE = os.environ.get(
    "XHS_COOKIE_FILE",
    os.path.expanduser("~/.config/xhs-downloader/cookie.txt")
)

# 下载目录
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", os.path.expanduser("~/Downloads/xhs"))

CST = timezone(timedelta(hours=8))

# ─── HTTP 工具 ─────────────────────────────────────────

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def http_post(url, data, headers=None):
    body = json.dumps(data).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

# ─── 飞书 API ─────────────────────────────────────────

def get_feishu_token():
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    r = http_post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", data)
    return r["tenant_access_token"]

def get_notes_from_feishu(token, only_undownloaded=True):
    """从飞书表格读取笔记链接"""
    url = (f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}"
           f"/tables/{BITABLE_TABLE_ID}/records?page_size=500")
    headers = {"Authorization": f"Bearer {token}"}
    notes = []
    page_token = None

    while True:
        paged_url = url + (f"&page_token={page_token}" if page_token else "")
        r = http_get(paged_url, headers)
        for rec in r.get("data", {}).get("items", []):
            fields = rec.get("fields", {})
            record_id = rec.get("record_id", "")

            # 提取链接
            link_field = fields.get("笔记链接", "")
            if isinstance(link_field, dict):
                link = link_field.get("link", "")
            elif isinstance(link_field, str):
                link = link_field
            else:
                continue

            if not link or "xiaohongshu.com" not in link:
                continue

            # 检查是否已下载
            downloaded = fields.get("已下载", "")
            if only_undownloaded and downloaded:
                continue

            notes.append({
                "record_id": record_id,
                "link": link,
                "title": fields.get("标题", ""),
                "author": fields.get("作者", ""),
            })

        if not r.get("data", {}).get("has_more"):
            break
        page_token = r["data"].get("page_token")

    return notes

def mark_downloaded(token, record_id):
    """在飞书表格中标记已下载"""
    url = (f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}"
           f"/tables/{BITABLE_TABLE_ID}/records/{record_id}")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    data = {"fields": {"已下载": now_ts}}
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return True
    except Exception as e:
        print(f"  ⚠️ 标记失败: {e}")
        return False

# ─── 下载 ─────────────────────────────────────────────

def download_note(link, download_dir, cookie_file):
    """调用 xhs-downloader 下载单条笔记"""
    # 优先用源码版
    downloader_src = os.path.expanduser(
        "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AI-System/mcp-servers/xhs-downloader-src"
    )
    venv_python = os.path.expanduser(
        "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/AI-System/mcp-servers/xhs-venv/bin/python"
    )

    if os.path.exists(downloader_src) and os.path.exists(venv_python):
        cmd = [
            venv_python, os.path.join(downloader_src, "main.py"),
            "--url", link,
            "--work_path", download_dir,
        ]
        if os.path.exists(cookie_file):
            with open(cookie_file) as f:
                cookie = f.read().strip()
            if cookie:
                cmd.extend(["--cookie", cookie])
    else:
        # 备用：如果有全局安装的 xhs-downloader
        cmd = [XHS_PYTHON, "-m", "XHS-Downloader",
               "--url", link,
               "--work_path", download_dir]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=download_dir,
        )
        if result.returncode == 0:
            return True
        else:
            print(f"  ⚠️ 下载异常: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ 下载超时（120s）")
        return False
    except Exception as e:
        print(f"  ⚠️ 下载失败: {e}")
        return False

# ─── 主流程 ───────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='飞书表格 → 小红书批量下载')
    parser.add_argument('--all', action='store_true', help='下载所有（包括已下载的）')
    parser.add_argument('--limit', '-n', type=int, default=0, help='最多下载条数（0=不限）')
    parser.add_argument('--output', '-o', help=f'下载目录（默认 {DOWNLOAD_DIR}）',
                        default=DOWNLOAD_DIR)
    parser.add_argument('--dry-run', action='store_true', help='只列出待下载，不实际下载')
    parser.add_argument('--no-mark', action='store_true', help='下载后不标记飞书表格')
    args = parser.parse_args()

    download_dir = args.output
    os.makedirs(download_dir, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"飞书表格 → 小红书批量下载")
    print(f"时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')} CST")
    print(f"下载目录: {download_dir}")
    print(f"{'='*50}")

    # 1. 获取飞书数据
    token = get_feishu_token()
    print("✅ 飞书 token 获取成功")

    only_new = not args.all
    notes = get_notes_from_feishu(token, only_undownloaded=only_new)
    print(f"📋 {'待下载' if only_new else '全部'} {len(notes)} 条笔记")

    if not notes:
        print("✅ 无待下载内容")
        return

    if args.limit > 0:
        notes = notes[:args.limit]
        print(f"   限制下载 {args.limit} 条")

    # 2. 逐条下载
    if args.dry_run:
        print("\n🔍 试运行，以下笔记将被下载：")
        for n in notes:
            print(f"  • {n['title']} | {n['author']} | {n['link']}")
        return

    success = 0
    fail = 0

    for i, note in enumerate(notes):
        print(f"\n[{i+1}/{len(notes)}] {note['title'] or '(无标题)'}")
        print(f"  链接: {note['link']}")

        ok = download_note(note['link'], download_dir, XHS_COOKIE_FILE)

        if ok:
            success += 1
            print(f"  ✅ 下载成功")
            if not args.no_mark:
                mark_downloaded(token, note['record_id'])
        else:
            fail += 1
            print(f"  ❌ 下载失败")

        # 间隔，避免风控
        if i < len(notes) - 1:
            time.sleep(3)

    print(f"\n{'='*50}")
    print(f"完成：成功 {success} / 失败 {fail} / 共 {len(notes)}")
    print(f"下载目录: {download_dir}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
