# Briefly - AI 驱动的 RSS 阅读器

Briefly 是一个 AI 驱动的 RSS 阅读器应用，可以自动抓取 RSS 源、使用关键词过滤、并通过 AI 生成文章摘要。

## 功能特性

- **RSS 订阅管理**：添加、启用/禁用、删除 RSS 源
- **自动抓取**：每小时自动抓取最新文章
- **关键词过滤**：支持多关键词 OR 逻辑，自动过滤不需要的文章
- **AI 摘要**：使用 OpenAI API 生成 100 字以内的文章摘要
- **收藏管理**：标记收藏、标记已读
- **Webhook 推送**：支持推送到企业微信、钉钉等平台
- **极简前端**：使用 Tailwind CSS + Vanilla JS 的简洁界面

## 技术栈

- **后端**：FastAPI + SQLAlchemy ORM + SQLite
- **RSS 解析**：feedparser
- **AI 总结**：OpenAI API
- **定时任务**：APScheduler
- **前端**：Vanilla JS + Tailwind CSS

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并配置相关参数：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# OpenAI API Key（用于 AI 摘要功能）
OPENAI_API_KEY=your_api_key_here

# 数据库路径
DATABASE_URL=sqlite+aiosqlite:///./data/briefly.db

# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=false

# 抓取间隔（分钟）
FETCH_INTERVAL_MINUTES=60

# Webhook 配置（可选）
WEBHOOK_ENABLED=false
WEBHOOK_URL=
```

### 3. 创建数据目录

```bash
mkdir -p data
```

### 4. 启动应用

**开发模式**：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**生产模式**：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. 访问应用

- 阅读页面：http://localhost:8000/
- 配置页面：http://localhost:8000/config.html
- API 文档：http://localhost:8000/docs

## Docker 部署

### 使用 Docker Compose

```bash
docker-compose up -d
```

### 手动构建

```bash
docker build -t briefly .
docker run -d -p 8000:8000 -v $(pwd)/data:/app/data --name briefly-app briefly
```

## 测试 RSS 源

以下是一些常用的测试 RSS 源：

- **GitHub Trending**：https://github.com/trending.atom
- **Hacker News**：https://hnrss.org/frontpage
- **TechCrunch**：https://techcrunch.com/feed/
- **少数派**：https://sspai.com/feed
- **掘金**：https://feed.me/feedx

## API 接口

### RSS 源管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/sources` | 获取 RSS 源列表 |
| POST | `/api/sources` | 添加 RSS 源 |
| GET | `/api/sources/{id}` | 获取 RSS 源详情 |
| PUT | `/api/sources/{id}` | 更新 RSS 源 |
| DELETE | `/api/sources/{id}` | 删除 RSS 源 |
| POST | `/api/sources/{id}/toggle` | 切换启用状态 |
| POST | `/api/sources/{id}/fetch` | 手动抓取 |

### 文章管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/articles` | 获取文章列表 |
| GET | `/api/articles/{id}` | 获取文章详情 |
| PUT | `/api/articles/{id}/read` | 标记已读 |
| PUT | `/api/articles/{id}/favorite` | 切换收藏 |
| POST | `/api/articles/{id}/summarize` | 生成 AI 摘要 |
| GET | `/api/articles/statistics` | 获取统计信息 |

### 关键词管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/keywords` | 获取关键词列表 |
| POST | `/api/keywords` | 添加关键词 |
| DELETE | `/api/keywords/{id}` | 删除关键词 |
| POST | `/api/keywords/{id}/toggle` | 切换启用状态 |

### 系统管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/status` | 获取系统状态 |
| POST | `/api/fetch` | 手动触发抓取 |
| POST | `/api/summarize` | 手动触发摘要 |
| POST | `/api/run-pipeline` | 运行完整流程 |
| POST | `/api/test/ai` | 测试 AI 功能 |

## 项目结构

```
briefly/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── models/
│   │   ├── database.py      # 数据库初始化
│   │   ├── rss_source.py    # RSS 源模型
│   │   ├── article.py       # 文章模型
│   │   └── keyword.py       # 关键词模型
│   ├── services/
│   │   ├── rss_service.py   # RSS 抓取服务
│   │   ├── keyword_service.py  # 关键词过滤服务
│   │   ├── ai_service.py    # AI 摘要服务
│   │   ├── scheduler_service.py # 定时任务服务
│   │   └── webhook_service.py   # Webhook 服务
│   ├── routes/
│   │   ├── sources.py       # RSS 源路由
│   │   ├── articles.py       # 文章路由
│   │   ├── keywords.py       # 关键词路由
│   │   └── system.py        # 系统路由
│   └── static/
│       ├── index.html       # 阅读页面
│       ├── config.html      # 配置页面
│       └── api.js           # API 客户端
├── data/                    # 数据库文件目录
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量示例
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 使用说明

### 添加 RSS 源

1. 打开配置页面（http://localhost:8000/config.html）
2. 在「RSS 源管理」部分点击「添加源」
3. 输入名称和 RSS URL
4. 点击「添加」

### 设置关键词过滤

1. 打开配置页面
2. 在「关键词过滤」部分点击「添加关键词」
3. 输入要过滤的关键词
4. 文章标题或内容包含该关键词将被标记为「过滤」

### 查看文章摘要

1. 在阅读页面点击文章卡片
2. 如果文章已有摘要，会显示 AI 摘要
3. 如果没有摘要，可以点击「生成摘要」按钮

## 常见问题

### Q: AI 摘要功能不工作
A: 请确保在 `.env` 文件中配置了正确的 `OPENAI_API_KEY`。

### Q: RSS 抓取失败
A: 请检查 RSS URL 是否正确，以及网络连接是否正常。

### Q: 如何查看日志
A: 应用运行时会输出日志到控制台，可以使用 `DEBUG=true` 开启调试模式。

## 许可证

MIT License
