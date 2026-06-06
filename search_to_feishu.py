#!/usr/bin/env python3
"""
小红书关键词搜索 → 飞书多维表格

批量搜索小红书关键词，将笔记信息自动写入飞书多维表格。
支持去重（按笔记链接）、分类标记、定时运行。

配置方式：
  1. 环境变量
  2. 配置文件 ~/.config/xhs-to-feishu/.env

依赖：pip install xhs browser_cookie3
"""

import json
import time
import os
import sys
import argparse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── 配置加载 ──────────────────────────────────────────

def load_env():
    """从配置文件加载环境变量"""
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
        print(f"   请设置环境变量或写入 ~/.config/xhs-to-feishu/.env", file=sys.stderr)
        sys.exit(1)
    return val

FEISHU_APP_ID     = require_env("FEISHU_APP_ID", "飞书应用 App ID")
FEISHU_APP_SECRET = require_env("FEISHU_APP_SECRET", "飞书应用 App Secret")
BITABLE_APP_TOKEN = require_env("BITABLE_APP_TOKEN", "飞书多维表格 App Token")
BITABLE_TABLE_ID  = require_env("BITABLE_TABLE_ID", "飞书多维表格 Table ID")

# Chrome Cookie 路径（用于小红书登录态）
CHROME_COOKIE_PATH = os.environ.get(
    "CHROME_COOKIE_PATH",
    os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cookies")
)

# 搜索间隔（秒），防风控
SLEEP_BETWEEN = int(os.environ.get("SLEEP_BETWEEN", "8"))
PAGE_SIZE = 20

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

def get_existing_links(token):
    """拉取飞书表格已有的笔记链接，用于去重"""
    url = (f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}"
           f"/tables/{BITABLE_TABLE_ID}/records?page_size=500")
    headers = {"Authorization": f"Bearer {token}"}
    existing = set()
    page_token = None
    while True:
        paged_url = url + (f"&page_token={page_token}" if page_token else "")
        r = http_get(paged_url, headers)
        for rec in r.get("data", {}).get("items", []):
            fields = rec.get("fields", {})
            link = fields.get("笔记链接", "")
            if isinstance(link, dict):
                existing.add(link.get("link", ""))
            elif isinstance(link, str):
                existing.add(link)
        if not r.get("data", {}).get("has_more"):
            break
        page_token = r["data"].get("page_token")
    return existing

def write_to_feishu(token, records):
    """批量写入飞书多维表格"""
    url = (f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}"
           f"/tables/{BITABLE_TABLE_ID}/records/batch_create")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    total = 0
    for i in range(0, len(records), 100):
        batch = records[i:i+100]
        body = json.dumps({"records": batch}).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode())
            created = len(result.get("data", {}).get("records", []))
            total += created
            print(f"  写入 {created} 条")
    return total

# ─── 小红书搜索 ───────────────────────────────────────

def get_cookie_str(profile_path):
    """从 Chrome 读取小红书 Cookie"""
    import browser_cookie3
    cj = browser_cookie3.chrome(
        cookie_file=profile_path,
        domain_name='.xiaohongshu.com'
    )
    cookie_str = '; '.join(f'{c.name}={c.value}' for c in cj)
    if not cookie_str:
        raise RuntimeError("未读取到小红书 Cookie，请确认 Chrome 已登录 xiaohongshu.com")
    return cookie_str

def search_keyword(client, keyword, pages=1):
    """搜索关键词，返回笔记列表"""
    from xhs import SearchSortType, SearchNoteType
    all_items = []
    for page in range(1, pages + 1):
        try:
            result = client.get_note_by_keyword(
                keyword,
                page=page,
                page_size=PAGE_SIZE,
                sort=SearchSortType.GENERAL,
                note_type=SearchNoteType.ALL,
            )
            items = result.get('items', [])
            all_items.extend(items)
            has_more = result.get('has_more', False)
            print(f"  第{page}页：{len(items)} 条 | has_more={has_more}")
            if not has_more or not items:
                break
            if page < pages:
                time.sleep(SLEEP_BETWEEN)
        except Exception as e:
            print(f"  ⚠️ 第{page}页搜索失败: {e}")
            break
    return all_items

def format_note(item):
    """提取笔记关键字段"""
    note = item.get('note_card', {})
    info = note.get('interact_info', {})
    user = note.get('user', {})
    return {
        'id': item.get('id', ''),
        'title': note.get('display_title', ''),
        'author': user.get('nickname', ''),
        'user_id': user.get('user_id', ''),
        'liked': info.get('liked_count', '0'),
        'collected': info.get('collected_count', '0'),
        'comments': info.get('comment_count', '0'),
        'type': note.get('type', ''),
        'url': f"https://www.xiaohongshu.com/explore/{item.get('id', '')}",
    }

# ─── 主流程 ───────────────────────────────────────────

def load_keywords(config_path=None):
    """加载关键词配置"""
    if config_path:
        path = Path(config_path)
    else:
        path = Path(__file__).parent / "keywords.json"

    if not path.exists():
        print(f"❌ 关键词配置文件不存在：{path}")
        print(f"   请复制 keywords.example.json 并编辑")
        sys.exit(1)

    with open(path) as f:
        config = json.load(f)

    if isinstance(config, list):
        return {"默认": config}
    elif isinstance(config.get('keywords'), dict):
        return config['keywords']
    else:
        return {"默认": config.get('keywords', [])}

def main():
    parser = argparse.ArgumentParser(description='小红书搜索 → 飞书多维表格')
    parser.add_argument('--keyword', '-k', help='单个关键词（不使用配置文件）')
    parser.add_argument('--config', '-c', help='关键词配置文件路径（默认 keywords.json）')
    parser.add_argument('--pages', '-p', type=int, default=1, help='每个关键词搜索页数')
    parser.add_argument('--profile', help='Chrome Cookie 路径', default=CHROME_COOKIE_PATH)
    parser.add_argument('--dry-run', action='store_true', help='只搜索不写入飞书')
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"小红书搜索 → 飞书多维表格")
    print(f"时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')} CST")
    print(f"{'='*50}")

    # 1. 加载关键词
    if args.keyword:
        keywords_map = {"手动": [args.keyword]}
    else:
        keywords_map = load_keywords(args.config)

    all_keywords = []
    for cat, kws in keywords_map.items():
        all_keywords.extend([(kw, cat) for kw in kws])
    print(f"\n📋 共 {len(all_keywords)} 个关键词")

    # 2. 初始化小红书客户端
    print(f"\n📥 读取 Chrome Cookie...")
    try:
        cookie_str = get_cookie_str(args.profile)
        has_web_session = 'web_session=' in cookie_str
        print(f"  web_session: {'✅' if has_web_session else '❌'}")
        if not has_web_session:
            print("\n⚠️  缺少 web_session Cookie！")
            print("解决：打开 Chrome → 访问 xiaohongshu.com → 确认已登录")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cookie 读取失败: {e}")
        sys.exit(1)

    from xhs import XhsClient
    from xhs.help import sign as _xhs_sign
    def get_sign(uri, data=None, a1="", web_session=""):
        return _xhs_sign(uri, data, a1=a1)
    client = XhsClient(cookie=cookie_str, sign=get_sign)

    # 3. 获取飞书已有链接（去重）
    if not args.dry_run:
        token = get_feishu_token()
        print("✅ 飞书 token 获取成功")
        existing_links = get_existing_links(token)
        print(f"📋 飞书已有 {len(existing_links)} 条笔记")
    else:
        existing_links = set()
        print("🔍 试运行模式，不写入飞书")

    # 4. 逐关键词搜索
    new_records = []
    today_ts = int(datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).timestamp() * 1000)

    print(f"\n🔍 开始搜索（每次间隔 {SLEEP_BETWEEN}s）\n")

    for i, (kw, cat) in enumerate(all_keywords):
        print(f"[{i+1}/{len(all_keywords)}] 搜索：{kw}（{cat}）")
        notes_raw = search_keyword(client, kw, pages=args.pages)
        notes = [format_note(item) for item in notes_raw]

        added = 0
        for note in notes:
            if note['url'] in existing_links:
                continue
            existing_links.add(note['url'])  # 本轮也去重

            record = {"fields": {
                "标题": note['title'] or "(无标题)",
                "作者": note['author'],
                "笔记链接": {"link": note['url'], "text": note['title'] or note['url']},
                "点赞": note['liked'],
                "收藏": note['collected'],
                "评论": note['comments'],
                "类型": "视频" if note['type'] == 'video' else "图文",
                "搜索词": kw,
                "分类": cat,
                "采集日期": today_ts,
            }}
            new_records.append(record)
            added += 1

        print(f"  ✅ {len(notes)} 条结果，新增 {added} 条\n")

        if i < len(all_keywords) - 1:
            time.sleep(SLEEP_BETWEEN)

    print(f"\n🆕 待写入 {len(new_records)} 条新笔记")

    if not new_records:
        print("✅ 无新内容，跳过写入")
        return

    # 5. 写入飞书
    if not args.dry_run:
        total = write_to_feishu(token, new_records)
        print(f"✅ 同步完成，写入 {total} 条")
    else:
        print("🔍 试运行完成，以下笔记将被写入：")
        for r in new_records[:10]:
            f = r['fields']
            print(f"  • {f['标题']} | {f['作者']} | 👍{f['点赞']} | {f['搜索词']}")
        if len(new_records) > 10:
            print(f"  ... 共 {len(new_records)} 条")


if __name__ == '__main__':
    main()
