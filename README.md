# 文墨 Wenmo

文墨是一个中文 AI 写作与沟通助手。当前仓库包含风格档案、风格写作工作台，以及
聊天助手的后端会话与人设能力。

## 项目结构

```text
QuillMind/backend/   Django REST API、LLM 网关与业务服务
frontend/            Vue 3 + TypeScript + Element Plus
docs/                用户指南与评测数据
scripts/             联调和验收脚本
```

## 环境要求

- Python 3.9+
- Node.js 20+
- PostgreSQL 15+
- Redis

后端必须配置：

```bash
DATABASE_URL=postgresql://...
OPENAI_API_KEY=...
REDIS_URL=redis://localhost:6379/0
DJANGO_SECRET_KEY=...
```

可选的风格生成参数：

```bash
STYLE_AI_FLAVOR_THRESHOLD=0.7
STYLE_SIMILARITY_THRESHOLD=0.75
STYLE_GENERATION_MAX_RETRIES=2
STYLE_GENERATION_TIMEOUT_SECONDS=30
CHAT_MAX_REPLY_LENGTH=150
CHAT_HISTORY_MESSAGE_LIMIT=40
CHAT_REPLY_BASE_TEMPERATURE=0.7
CHAT_REGENERATE_TEMPERATURE=1.0
```

## 启动后端

```bash
cd QuillMind
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

API 文档：`http://127.0.0.1:8000/api/docs/`

聊天流使用 WebSocket：

```text
ws://127.0.0.1:8000/ws/chat/{session_id}/?token={JWT_ACCESS_TOKEN}
```

发送 `{"action":"message","content":"对方说的话"}` 获取 token 流；发送
`{"action":"regenerate"}` 可基于同一上下文换一条回复。

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：`http://127.0.0.1:5173/`

## 验证

```bash
cd QuillMind/backend
python manage.py test
python manage.py spectacular --file /tmp/quillmind-schema.yml --validate
```

模块二 MVP 的三账号全链路验收：

```bash
export WENMO_BASE_URL="https://your-dev-host.example.com"
export WENMO_E2E_PASSWORD="一次性测试密码"
python scripts/style_mvp_e2e.py
```

详细操作见 [风格写作用户指南](docs/user-guide-style.md)。11
