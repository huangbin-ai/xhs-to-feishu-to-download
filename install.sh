#!/bin/bash
# 小红书监测 + 飞书同步 — 安装脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$HOME/.config/xhs-to-feishu"
ENV_FILE="$CONFIG_DIR/.env"
PYTHON3="$(command -v python3 || true)"

echo ""
echo "═══════════════════════════════════════════════"
echo "  小红书 → 飞书多维表格 安装脚本"
echo "═══════════════════════════════════════════════"
echo ""

# ── 1. 检查 Python ────────────────────────────────────

if [[ -z "$PYTHON3" ]]; then
  echo "❌ 未找到 python3，请先安装：brew install python3"
  exit 1
fi
echo "✅ Python3: $PYTHON3"

# ── 2. 检查依赖 ──────────────────────────────────────

echo ""
echo "⏳ 检查 Python 依赖..."

check_pip() {
  $PYTHON3 -c "import $1" 2>/dev/null
}

MISSING=""
if ! check_pip "xhs"; then
  MISSING="$MISSING xhs"
fi
if ! check_pip "browser_cookie3"; then
  MISSING="$MISSING browser_cookie3"
fi

if [[ -n "$MISSING" ]]; then
  echo "⚠️  缺少依赖：$MISSING"
  echo "   安装命令：pip3 install$MISSING"
  read -p "   是否现在安装？(y/N) " yn
  if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
    pip3 install $MISSING --break-system-packages 2>/dev/null || pip3 install $MISSING
    echo "✅ 依赖安装完成"
  else
    echo "请手动安装后重新运行"
    exit 1
  fi
else
  echo "✅ Python 依赖齐全（xhs, browser_cookie3）"
fi

# ── 3. 检查 xhs-downloader（下载功能需要）───────────────

echo ""
XHS_SRC="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/AI-System/mcp-servers/xhs-downloader-src"
if [[ -d "$XHS_SRC" ]]; then
  echo "✅ xhs-downloader 已安装（源码版）"
else
  echo "⚠️  xhs-downloader 未安装（下载功能不可用）"
  echo "   安装方法：git clone https://github.com/JoeanAmier/XHS-Downloader.git"
  echo "   搜索功能不受影响，可以先跳过"
fi

# ── 4. 生成配置文件 ───────────────────────────────────

echo ""
if [[ -f "$ENV_FILE" ]]; then
  echo "✅ 配置文件已存在：$ENV_FILE"
else
  mkdir -p "$CONFIG_DIR"
  cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
  echo "📝 配置文件已生成：$ENV_FILE"
  echo ""
  echo "   ⚠️  请先编辑配置文件，填入飞书应用凭证："
  echo "   vim $ENV_FILE"
  echo ""
  echo "   填完后重新运行此脚本。"
  exit 0
fi

# ── 5. 生成关键词配置 ─────────────────────────────────

if [[ -f "$SCRIPT_DIR/keywords.json" ]]; then
  echo "✅ 关键词配置已存在：keywords.json"
else
  cp "$SCRIPT_DIR/keywords.example.json" "$SCRIPT_DIR/keywords.json"
  echo "📝 关键词配置已生成：keywords.json"
  echo "   请编辑填入你要监测的关键词"
fi

# ── 6. 验证飞书配置 ──────────────────────────────────

echo ""
source "$ENV_FILE" 2>/dev/null || true

MISSING_CFG=0
for VAR in FEISHU_APP_ID FEISHU_APP_SECRET BITABLE_APP_TOKEN BITABLE_TABLE_ID; do
  VAL="${!VAR:-}"
  if [[ -z "$VAL" || "$VAL" == "你的"* ]]; then
    echo "❌ 配置未填写：$VAR"
    MISSING_CFG=1
  fi
done

if [[ $MISSING_CFG -eq 1 ]]; then
  echo ""
  echo "请编辑配置文件后重新运行：vim $ENV_FILE"
  exit 1
fi
echo "✅ 飞书配置检查通过"

# ── 完成 ──────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════"
echo "  安装完成！"
echo ""
echo "  搜索并写入飞书："
echo "    python3 $SCRIPT_DIR/search_to_feishu.py"
echo ""
echo "  从飞书下载内容："
echo "    python3 $SCRIPT_DIR/download_from_feishu.py"
echo ""
echo "  试运行（不实际写入/下载）："
echo "    python3 search_to_feishu.py --dry-run"
echo "    python3 download_from_feishu.py --dry-run"
echo ""
echo "  配置文件：$ENV_FILE"
echo "  关键词配置：$SCRIPT_DIR/keywords.json"
echo "═══════════════════════════════════════════════"
