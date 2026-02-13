# 📰 Briefly - AI 驱动的智能 RSS 阅读器

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

<p align="center">
  <b>让信息阅读更高效</b><br>
  <sub>自动抓取 · 智能过滤 · AI 摘要 · 极简体验</sub>
</p>

---

## ✨ 核心特性

### 🔔 智能订阅管理
- **多源订阅** - 支持添加多个 RSS 源，一键启用/禁用
- **自动抓取** - 定时自动获取最新文章，无需手动刷新
- **实时同步** - 跨标签页状态同步，配置即时生效

### 🎯 精准内容过滤
- **关键词过滤** - 设置关键词，自动过滤不感兴趣的内容
- **智能匹配** - 支持标题和内容双重匹配
- **灵活控制** - 随时启用/禁用过滤规则

### 🤖 AI 智能摘要
- **一键摘要** - 使用 AI 自动生成 100 字以内的精炼摘要
- **批量处理** - 定时自动为未摘要文章生成摘要
- **多模型支持** - 兼容 OpenAI、智谱 AI 等 API

### 💎 优雅阅读体验
- **双视图模式** - 卡片视图 / 列表视图自由切换
- **搜索功能** - 快速搜索文章标题
- **收藏管理** - 收藏喜欢的文章，随时回顾
- **已读追踪** - 自动标记已读，未读文章一目了然

### 🔔 Webhook 推送
- 支持推送到企业微信、钉钉、飞书等平台
- **定时推送** - 默认每小时推送，可配置每天/每周/每月
- 可选择推送收藏文章或过滤文章

---

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn |
| **数据库** | SQLite + SQLAlchemy ORM (异步) |
| **RSS 解析** | feedparser |
| **AI 服务** | OpenAI API / 智谱 AI |
| **定时任务** | APScheduler |
| **前端** | Vanilla JS + Tailwind CSS |

---

## 🚀 快速开始

### 方式一：本地运行

```bash
# 1. 克隆项目
git clone https://github.com/xulin3344/Briefly.git
cd Briefly

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置 API Key 等参数

# 4. 创建数据目录
mkdir -p data

# 5. 启动应用
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 方式二：Docker 部署

```bash
# 使用 Docker Compose（推荐）
docker-compose up -d

# 或手动构建
docker build -t briefly .
docker run -d -p 8000:8000 -v $(pwd)/data:/app/data --name briefly-app briefly
```

### 访问应用

| 页面 | 地址 |
|------|------|
| 📖 阅读页面 | http://localhost:8000/ |
| ⚙️ 配置页面 | http://localhost:8000/config.html |
| 📚 API 文档 | http://localhost:8000/docs |

---

## ⚙️ 配置说明

创建 `.env` 文件并配置以下参数：

```env
# ========== AI 配置 ==========
# OpenAI API Key（用于 AI 摘要功能）
OPENAI_API_KEY=your_api_key_here
# API Base URL（可选，用于自定义 API 端点）
OPENAI_BASE_URL=https://api.openai.com/v1
# 模型名称
OPENAI_MODEL=gpt-3.5-turbo

# ========== 数据库配置 ==========
DATABASE_URL=sqlite+aiosqlite:///./data/briefly.db

# ========== 服务器配置 ==========
HOST=0.0.0.0
PORT=8000
DEBUG=false

# ========== 定时任务配置 ==========
# RSS 抓取间隔（分钟）
FETCH_INTERVAL_MINUTES=60

# ========== Webhook 配置（可选）==========
WEBHOOK_ENABLED=false
WEBHOOK_URL=
```

---

## 📖 使用指南

### 添加 RSS 源

1. 打开 [配置页面](http://localhost:8000/config.html)
2. 在「RSS 源管理」区域点击「添加源」
3. 输入名称和 RSS URL，点击「添加」
4. 系统会自动验证 RSS 源并开始抓取

### 设置关键词过滤

1. 在配置页面的「关键词过滤」区域点击「添加关键词」
2. 输入要过滤的关键词
3. 包含该关键词的文章将被自动标记为「已过滤」

### 使用 AI 摘要

1. 点击文章卡片打开详情
2. 如果文章已有摘要，会显示在顶部蓝色区域
3. 没有摘要时，点击「生成摘要」按钮即可

---

## 📡 API 接口

### RSS 源管理

```
GET    /api/sources           # 获取 RSS 源列表
POST   /api/sources           # 添加 RSS 源
GET    /api/sources/{id}      # 获取 RSS 源详情
PUT    /api/sources/{id}      # 更新 RSS 源
DELETE /api/sources/{id}      # 删除 RSS 源
POST   /api/sources/{id}/toggle  # 切换启用状态
```

### 文章管理

```
GET    /api/articles          # 获取文章列表（支持分页、筛选、搜索）
GET    /api/articles/{id}     # 获取文章详情
PUT    /api/articles/{id}/read   # 标记已读
PUT    /api/articles/{id}/favorite  # 切换收藏
POST   /api/articles/{id}/summarize  # 生成 AI 摘要
GET    /api/articles/favorites  # 获取收藏列表
GET    /api/articles/statistics  # 获取统计信息
```

### 关键词管理

```
GET    /api/keywords          # 获取关键词列表
POST   /api/keywords          # 添加关键词
DELETE /api/keywords/{id}     # 删除关键词
POST   /api/keywords/{id}/toggle  # 切换启用状态
POST   /api/keywords/apply-filter  # 应用关键词过滤
```

### 系统管理

```
GET    /api/health            # 健康检查
GET    /api/status            # 获取系统状态
POST   /api/fetch             # 手动触发 RSS 抓取
POST   /api/fetch/start       # 后台触发 RSS 抓取
POST   /api/summarize         # 手动触发 AI 摘要
POST   /api/run-pipeline      # 运行完整流程
```

### Webhook 管理

```
GET    /api/webhook/config    # 获取 Webhook 配置
POST   /api/webhook/config    # 更新 Webhook 配置
POST   /api/webhook/test      # 测试 Webhook 连接
POST   /api/webhook/push-favorites   # 推送收藏文章
POST   /api/webhook/push-filtered   # 推送过滤文章
```

---

## 📁 项目结构

```
briefly/
├── app/
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── models/
│   │   ├── database.py         # 数据库初始化
│   │   ├── rss_source.py      # RSS 源模型
│   │   ├── article.py         # 文章模型
│   │   ├── keyword.py         # 关键词模型
│   │   ├── ai_settings.py     # AI 设置模型
│   │   └── webhook_config.py  # Webhook 配置模型
│   ├── services/
│   │   ├── rss_service.py      # RSS 抓取服务
│   │   ├── keyword_service.py  # 关键词过滤服务
│   │   ├── ai_service.py       # AI 摘要服务
│   │   ├── ai_filter_service.py # AI 过滤服务
│   │   ├── scheduler_service.py # 定时任务服务
│   │   ├── webhook_service.py  # Webhook 服务
│   │   └── webhook_scheduler.py # Webhook 定时推送
│   ├── routes/
│   │   ├── sources.py          # RSS 源路由
│   │   ├── articles.py         # 文章路由
│   │   ├── keywords.py         # 关键词路由
│   │   ├── webhook.py          # Webhook 路由
│   │   └── system.py           # 系统路由
│   └── static/
│       ├── index.html          # 阅读页面
│       ├── config.html         # 配置页面
│       └── api.js              # API 客户端
├── data/                       # 数据库文件目录
├── tests/                      # 测试文件
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量示例
├── Dockerfile                  # Docker 构建文件
├── docker-compose.yml          # Docker Compose 配置
└── README.md
```

---

## 🔗 推荐 RSS 源

| 名称 | RSS 地址 |
|------|----------|
| GitHub Blog | https://github.blog/feed/ |
| Hacker News | https://hnrss.org/frontpage |
| 36氪 | https://www.36kr.com/feed |
| 少数派 | https://sspai.com/feed |
| TechCrunch | https://techcrunch.com/feed/ |

---

## ❓ 常见问题

<details>
<summary><b>Q: AI 摘要功能不工作？</b></summary>

请确保在 `.env` 文件中配置了正确的 `OPENAI_API_KEY`。如果使用智谱 AI，需要设置：
```env
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4
```
</details>

<details>
<summary><b>Q: RSS 抓取失败？</b></summary>

1. 检查 RSS URL 是否正确
2. 确认网络连接正常
3. 查看控制台日志获取详细错误信息
4. 部分网站可能有访问限制，尝试使用代理
</details>

<details>
<summary><b>Q: 如何查看运行日志？</b></summary>

应用运行时会输出日志到控制台。开启调试模式可获取更详细信息：
```env
DEBUG=true
```
</details>

<details>
<summary><b>Q: 数据存储在哪里？</b></summary>

数据存储在 SQLite 数据库中，默认路径为 `./data/briefly.db`。可以通过 `DATABASE_URL` 环境变量修改。
</details>

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

---

<p align="center">
  Made with ❤️ by Briefly Team
</p>
