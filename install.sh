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

# ── 5. 生成关键词 & 账号配置 ──────────────────────────

if [[ -f "$SCRIPT_DIR/keywords.json" ]]; then
  echo "✅ 关键词配置已存在：keywords.json"
else
  cp "$SCRIPT_DIR/keywords.example.json" "$SCRIPT_DIR/keywords.json"
  echo "📝 关键词配置已生成：keywords.json"
  echo "   请编辑填入你要监测的关键词"
fi

if [[ -f "$SCRIPT_DIR/accounts.json" ]]; then
  echo "✅ 账号配置已存在：accounts.json"
else
  cp "$SCRIPT_DIR/accounts.example.json" "$SCRIPT_DIR/accounts.json"
  echo "📝 账号配置已生成：accounts.json"
  echo "   请编辑填入你要监测的小红书账号"
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

# ── 7. 注册 cron 定时任务 ─────────────────────────────

echo ""
LOG_FILE="$HOME/Library/Logs/xhs-to-feishu.log"
CRON_CMD="0 9 * * * cd $SCRIPT_DIR && $PYTHON3 monitor_accounts.py >> $LOG_FILE 2>&1"

if crontab -l 2>/dev/null | grep -q "xhs-to-feishu"; then
  echo "✅ cron 定时任务已存在，跳过"
else
  read -p "是否注册每日定时监测（每天 9:00 自动运行）？(y/N) " yn
  if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
    (crontab -l 2>/dev/null; echo "# 小红书账号监测 - 每天 9:00") | crontab -
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ cron 定时任务已注册（每天 09:00 执行账号监测）"
  else
    echo "⏭️  跳过定时任务，后续可手动注册"
  fi
fi

# ── 完成 ──────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════"
echo "  安装完成！"
echo ""
echo "  📌 账号监测（每日定时）："
echo "    python3 $SCRIPT_DIR/monitor_accounts.py"
echo ""
echo "  🔍 关键词搜索："
echo "    python3 $SCRIPT_DIR/search_to_feishu.py"
echo ""
echo "  📥 从飞书批量下载："
echo "    python3 $SCRIPT_DIR/download_from_feishu.py"
echo ""
echo "  🧪 试运行（不实际写入/下载）："
echo "    python3 monitor_accounts.py --dry-run"
echo "    python3 search_to_feishu.py --dry-run"
echo "    python3 download_from_feishu.py --dry-run"
echo ""
echo "  ⚙️  配置文件："
echo "    飞书凭证：$ENV_FILE"
echo "    监测账号：$SCRIPT_DIR/accounts.json"
echo "    搜索关键词：$SCRIPT_DIR/keywords.json"
echo "    运行日志：$LOG_FILE"
echo "═══════════════════════════════════════════════"
