# 小红书账号监测 → 飞书多维表格 → 批量下载

批量监测小红书账号和关键词，每天自动采集新笔记写入飞书多维表格，一键批量下载图片/视频到本地。

## 三步工作流

```
第一步：账号监测 → 飞书（每天自动运行）
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  accounts.json│ →  │ 小红书 API    │ →  │ 飞书多维表格  │
│  监测账号列表  │    │ 获取最新笔记  │    │  自动写入     │
└──────────────┘    └──────────────┘    └──────────────┘

第一步（备选）：关键词搜索 → 飞书
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ keywords.json │ →  │ 小红书 API    │ →  │ 飞书多维表格  │
│  关键词配置   │    │  搜索笔记     │    │  自动写入     │
└──────────────┘    └──────────────┘    └──────────────┘

第二步：飞书 → 批量下载
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 飞书多维表格   │ →  │ xhs-downloader│ →  │ 本地文件夹   │
│  读取链接     │    │  逐条下载     │    │  图片/视频    │
└──────────────┘    └──────────────┘    └──────────────┘
```

## 功能

- **账号批量监测** — 配置要关注的小红书账号，每天自动抓取最新笔记
- **关键词搜索** — 按分类配置关键词，批量搜索采集
- **自动写入飞书** — 标题、作者、点赞/收藏/评论数、链接自动入表
- **智能去重** — 按笔记链接去重，重复运行不会重复写入
- **定时运行** — cron 每天 9:00 自动监测，无需手动操作
- **批量下载** — 从飞书表格读取链接，一键下载所有图片/视频
- **下载标记** — 已下载的笔记自动标记，支持断点续传
- **试运行** — `--dry-run` 只看结果不实际执行，放心调试
- **零第三方框架** — 飞书 API 用纯 Python 标准库，不依赖 SDK

---

## 前置准备（约 15 分钟，只需做一次）

### 1. 创建飞书应用

1. 打开 [飞书开放平台](https://open.feishu.cn/app)，登录
2. 创建企业自建应用
3. 记录 **App ID** 和 **App Secret**
4. 开通权限：`bitable:app:readonly`、`bitable:app`
5. 发布应用

### 2. 创建飞书多维表格

创建以下字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 标题 | 文本 | 笔记标题 |
| 作者 | 文本 | 小红书用户名 |
| 笔记链接 | 超链接 | 笔记原文链接 |
| 点赞 | 文本 | 点赞数 |
| 收藏 | 文本 | 收藏数 |
| 评论 | 文本 | 评论数 |
| 类型 | 文本 | 图文 / 视频 |
| 搜索词 | 文本 | 搜索关键词或 @账号名 |
| 分类 | 文本 | 关键词分类或账号备注 |
| 采集日期 | 日期 | 采集时间 |
| 已下载 | 日期 | 下载完成时间（自动标记）|

在表格中添加你创建的飞书应用（表格右上角 → 更多 → 添加文档应用）。

### 3. 保持小红书登录

用 Chrome 浏览器登录 [小红书](https://www.xiaohongshu.com)，脚本会自动读取 Cookie。

---

## 安装

```bash
git clone https://github.com/huangbin-ai/xhs-to-feishu-to-download.git
cd xhs-to-feishu-to-download
chmod +x install.sh
./install.sh
```

安装脚本会：

1. ✅ 检查 Python 和依赖
2. ✅ 生成配置文件
3. ✅ 生成账号列表和关键词配置
4. ✅ 验证飞书凭证
5. ✅ 可选注册 cron 定时任务（每天 9:00）

首次运行按提示编辑三个配置：

```bash
vim ~/.config/xhs-to-feishu/.env   # 飞书应用凭证
vim accounts.json                   # 要监测的小红书账号
vim keywords.json                   # 要搜索的关键词（可选）
```

---

## 使用

### 账号监测（核心功能，支持定时）

```bash
# 监测所有配置的账号，新笔记写入飞书
python3 monitor_accounts.py

# 每个账号多抓几页（默认 1 页约 30 条）
python3 monitor_accounts.py -p 3

# 试运行（不写入飞书）
python3 monitor_accounts.py --dry-run
```

安装时如果注册了 cron，每天 9:00 会自动运行。

### 关键词搜索（按需使用）

```bash
# 批量搜索（使用 keywords.json）
python3 search_to_feishu.py

# 搜索单个关键词
python3 search_to_feishu.py -k "AI营销"

# 多页搜索
python3 search_to_feishu.py -p 3

# 试运行
python3 search_to_feishu.py --dry-run
```

### 从飞书批量下载

```bash
# 下载所有未下载的笔记内容
python3 download_from_feishu.py

# 限制下载数量
python3 download_from_feishu.py -n 10

# 指定下载目录
python3 download_from_feishu.py -o ~/Downloads/xhs

# 试运行（只列出待下载）
python3 download_from_feishu.py --dry-run
```

---

## 账号配置

编辑 `accounts.json`，填入要监测的小红书账号：

```json
{
  "accounts": [
    {
      "name": "某博主",
      "user_id": "5a1234567890abcdef",
      "note": "竞品"
    },
    {
      "name": "另一个博主",
      "user_id": "https://www.xiaohongshu.com/user/profile/xxxxx",
      "note": "行业KOL"
    }
  ]
}
```

- `name`：备注名，会写入飞书「作者」字段
- `user_id`：小红书用户 ID（从用户主页 URL 获取），也可以直接填完整 URL
- `note`：分类备注（可选），会写入飞书「分类」字段

**获取用户 ID 方法**：打开某个小红书用户主页，URL 中 `/user/profile/` 后面那串就是 user_id。

## 关键词配置

编辑 `keywords.json`，按分类组织关键词：

```json
{
  "keywords": {
    "行业关注": ["关键词A", "关键词B"],
    "竞品观察": ["关键词C", "关键词D"],
    "选题参考": ["关键词E", "关键词F"]
  }
}
```

分类名会写入飞书表格的「分类」字段，方便后续筛选。

---

## 配置项说明

| 变量 | 说明 | 必填 |
|------|------|------|
| `FEISHU_APP_ID` | 飞书应用 App ID | ✅ |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret | ✅ |
| `BITABLE_APP_TOKEN` | 飞书多维表格 Token | ✅ |
| `BITABLE_TABLE_ID` | 飞书多维表格 Table ID | ✅ |
| `CHROME_COOKIE_PATH` | Chrome Cookie 路径 | 默认自动检测 |
| `XHS_COOKIE_FILE` | xhs-downloader Cookie | 下载功能需要 |
| `DOWNLOAD_DIR` | 下载目录 | 默认 ~/Downloads/xhs |
| `SLEEP_BETWEEN` | 请求间隔秒数 | 默认 8 |

## 日常使用

安装完成后**账号监测自动运行**（如果注册了 cron），每天 9:00 自动采集新笔记。

```bash
# 查看运行日志
tail -f ~/Library/Logs/xhs-to-feishu.log

# 查看定时任务
crontab -l | grep xhs

# 手动触发一次
python3 monitor_accounts.py
```

需要下载内容时，手动运行：
```bash
python3 download_from_feishu.py
```

## 底层依赖

- [xhs](https://pypi.org/project/xhs/) — 小红书 Python SDK
- [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) — 小红书笔记下载工具
- [飞书开放平台](https://open.feishu.cn/) — 多维表格 API

## License

MIT
