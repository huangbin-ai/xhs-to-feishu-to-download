# 小红书笔记监测 → 飞书多维表格 + 批量下载

批量监测小红书关键词，自动采集笔记信息写入飞书多维表格，再从表格一键批量下载图片/视频。

## 两步工作流

```
第一步：搜索 → 飞书
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  关键词配置    │ →  │ 小红书 API    │ →  │ 飞书多维表格  │
│ keywords.json │    │  搜索笔记     │    │  自动写入     │
└──────────────┘    └──────────────┘    └──────────────┘

第二步：飞书 → 下载
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 飞书多维表格   │ →  │ xhs-downloader│ →  │ 本地文件夹   │
│  读取链接     │    │  逐条下载     │    │  图片/视频    │
└──────────────┘    └──────────────┘    └──────────────┘
```

## 功能

- **批量关键词监测** — 按分类配置关键词，一次搜索全部采集
- **自动写入飞书** — 笔记标题、作者、点赞/收藏/评论数、链接自动入表
- **智能去重** — 按笔记链接去重，重复运行不会重复写入
- **批量下载** — 从飞书表格读取链接，一键下载所有图片/视频
- **下载标记** — 已下载的笔记自动标记，支持断点续传
- **试运行** — `--dry-run` 只看结果不实际执行，放心调试
- **零第三方框架** — 飞书 API 用纯 Python 标准库，不依赖 SDK

## 前置准备

### 1. 创建飞书应用

1. 打开 [飞书开放平台](https://open.feishu.cn/app)，登录
2. 创建企业自建应用
3. 记录 **App ID** 和 **App Secret**
4. 开通权限：`bitable:app:readonly`、`bitable:app`
5. 发布应用

### 2. 创建飞书多维表格

创建以下字段：

| 字段名 | 类型 |
|--------|------|
| 标题 | 文本 |
| 作者 | 文本 |
| 笔记链接 | 超链接 |
| 点赞 | 文本 |
| 收藏 | 文本 |
| 评论 | 文本 |
| 类型 | 文本 |
| 搜索词 | 文本 |
| 分类 | 文本 |
| 采集日期 | 日期 |
| 已下载 | 日期 |

在表格中添加你创建的飞书应用（表格右上角 → 更多 → 添加文档应用）。

### 3. 保持小红书登录

用 Chrome 浏览器登录 [小红书](https://www.xiaohongshu.com)，脚本会自动读取 Cookie。

## 安装

```bash
git clone https://github.com/huangbin-ai/xhs-to-feishu.git
cd xhs-to-feishu
chmod +x install.sh
./install.sh
```

安装脚本会检查依赖、生成配置文件。按提示编辑：

```bash
vim ~/.config/xhs-to-feishu/.env     # 填入飞书凭证
vim keywords.json                     # 填入监测关键词
```

## 使用

### 第一步：搜索并写入飞书

```bash
# 批量搜索（使用 keywords.json 配置）
python3 search_to_feishu.py

# 搜索单个关键词
python3 search_to_feishu.py -k "AI营销"

# 多页搜索（每个关键词搜 3 页）
python3 search_to_feishu.py -p 3

# 试运行（不写入飞书）
python3 search_to_feishu.py --dry-run
```

### 第二步：从飞书下载内容

```bash
# 下载所有未下载的笔记
python3 download_from_feishu.py

# 限制下载数量
python3 download_from_feishu.py -n 10

# 指定下载目录
python3 download_from_feishu.py -o ~/Downloads/xhs

# 试运行（只列出待下载）
python3 download_from_feishu.py --dry-run
```

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
| `SLEEP_BETWEEN` | 搜索间隔秒数 | 默认 8 |

## 底层依赖

- [xhs](https://pypi.org/project/xhs/) — 小红书 Python SDK
- [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) — 小红书笔记下载工具
- [飞书开放平台](https://open.feishu.cn/) — 多维表格 API

## License

MIT
