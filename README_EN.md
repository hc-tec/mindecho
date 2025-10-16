# MindEcho (思维回响)

<div align="center">

**让收藏不再沉默，让知识产生回响**

*Your personal cognitive companion that transforms passive information hoarding into active knowledge synthesis*

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Nuxt 3](https://img.shields.io/badge/nuxt-3.x-00DC82.svg)](https://nuxt.com/)
[![License](https://img.shields.io/badge/license-Private-red.svg)](LICENSE)

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Documentation](#documentation)

</div>

---

## 💡 The Problem

We live in a paradox: **we collect information faster than ever, yet forget it with equal efficiency**.

- 📱 Your Bilibili favorites? **8,000+ videos, never watched again**
- 📕 Your小红书 collections? **Information graveyards, not inspiration goldmines**
- 📚 Your notes app? **Isolated fragments, disconnected insights**
- 🤖 Your AI tools? **Require manual input, copy-paste friction**

**The real bottleneck isn't storage—it's transformation.**

---

## ✨ The MindEcho Solution

MindEcho is not just another information manager. It's a **personal cognitive companion** that automatically transforms your scattered digital collections into an **interconnected knowledge network**.

### Four Strategic Pillars

#### 🔒 **1. Absolute Privacy & Data Sovereignty**
> *"Your thoughts belong only to you."*

- ✅ **100% local execution** — no cloud processing, no data collection
- ✅ **Your data, your rules** — complete control over your information
- ✅ **Offline-capable** — works without internet once set up

#### 🤖 **2. Deep Automation & Proactive Intelligence**
> *"Before you forget, MindEcho has already thought for you."*

- ✅ **Zero-intervention automation** — works silently in the background
- ✅ **Smart monitoring** — watches your favorite platforms 24/7
- ✅ **Auto-triggered processing** — AI analysis starts the moment you click "favorite"

#### 🕸️ **3. Connected Knowledge Network** *(Coming Soon)*
> *"Activate your entire knowledge base—let every collection echo through your mind."*

- 🔜 **Semantic linking** — auto-connect new content with your knowledge history
- 🔜 **Knowledge graph** — visualize relationships between ideas
- 🔜 **Smart recommendations** — surface forgotten insights when relevant

#### ⚡ **4. All-in-One Workflow**
> *"From information noise to final product, in one step."*

- ✅ **Multi-modal input** — video, images, text (supports Bilibili, 小红书)
- ✅ **AI processing** — summary, deep analysis, counterpoint debates
- ✅ **Structured output** — reports, insights, action items
- ✅ **Replaces 5-6 tools** — one unified experience

---

## 🎯 Features

### For Content Consumers

| Feature | Description | Status |
|---------|-------------|--------|
| 🎬 **Auto-Sync Collections** | Automatically sync your Bilibili/小红书 favorites | ✅ Ready |
| 📊 **Smart Dashboard** | Visual overview of all your knowledge activities | ✅ Ready |
| 🔍 **Global Search** | Search across titles, descriptions, and AI insights | ✅ Ready |
| 📥 **Inbox Triage** | Process pending items with one click | ✅ Ready |
| 🏷️ **Smart Tagging** | Organize with tags, filter by platform/author | ✅ Ready |

### For Knowledge Workers

| Feature | Description | Status |
|---------|-------------|--------|
| 🧠 **AI Workshops** | Multiple analysis modes (summary, deep insight, debate) | ✅ Ready |
| ⚙️ **Custom Workflows** | Create your own analysis pipelines | ✅ Ready |
| 🔄 **Auto-Trigger** | Bind workshops to collections for automatic processing | ✅ Ready |
| 📝 **Result Management** | Edit, regenerate, or delete AI outputs | ✅ Ready |
| 🎨 **Multi-Platform** | Unified interface for all your sources | ✅ Ready |

### Built-in AI Workshops

| Workshop | Purpose | Example Output |
|----------|---------|---------------|
| 📖 **精准摘要** | Extract core ideas | "3 key points in 100 words" |
| 💎 **快照洞察** | Deep analysis | "Hidden patterns & implications" |
| ⚗️ **信息炼金术** | Cross-reference synthesis | "Connect ideas across 5 sources" |
| ⚔️ **观点对撞** | Devil's advocate | "3 counterarguments to this claim" |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+** (for backend)
- **Node.js 18+** (for frontend)
- **Git** (for cloning)

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/your-username/mindecho.git
cd mindecho
```

#### 2. Set Up Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env
# Edit .env and configure:
# - DATABASE_URL (default: sqlite+aiosqlite:///./mindecho.db)
# - EAI_BASE_URL (your RPC service endpoint)
# - EAI_API_KEY (your API key)
# - BILIBILI_COOKIE_IDS (your Bilibili auth cookies)
# - XIAOHONGSHU_COOKIE_IDS (your 小红书 auth cookies)

# Start backend server
uvicorn app.main:app --reload --port 8000
```

The backend API will be available at `http://localhost:8000`

#### 3. Set Up Frontend

```bash
# Navigate to frontend directory (in a new terminal)
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3001`

#### 4. Initial Configuration

1. **Open your browser** → `http://localhost:3001`
2. **Go to Settings** → Configure your AI model and preferences
3. **Sync Collections** → Settings → Listening Management → Enable workshops
4. **Bind Collections** → Link your favorite folders to specific workshops
5. **Start Collecting** → Favorite content on Bilibili/小红书 and watch MindEcho work!

---

## 📚 How It Works

### The Automatic Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ 1. You favorite content on Bilibili/小红书                  │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. MindEcho monitors via continuous stream                  │
│    • Detects new favorites in real-time                     │
│    • No manual sync required                                │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Auto-fetches complete details                            │
│    • Video metadata, statistics                             │
│    • Subtitles (first 100 lines)                            │
│    • Author info, tags                                      │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Triggers bound workshop                                  │
│    • Collection "深度思考" → Workshop "快照洞察"           │
│    • Collection "学习资料" → Workshop "精准摘要"           │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. AI analyzes content in background                        │
│    • Processes rich context (title, intro, subtitles)       │
│    • Generates structured insights                          │
│    • Saves to local database                                │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Results available instantly                              │
│    • View in Dashboard                                      │
│    • Search, edit, regenerate                               │
│    • All data stays local                                   │
└─────────────────────────────────────────────────────────────┘
```

### Smart Routing

MindEcho intelligently routes content to the right workshop:

```python
# Example: Collection → Workshop Bindings
{
  "快照洞察": {
    "bilibili": ["深度思考", "哲学思辨"],
    "xiaohongshu": ["读书笔记"]
  },
  "精准摘要": {
    "bilibili": ["技术教程", "学习资料"]
  }
}
```

**Result:** Videos favorited in "深度思考" automatically get deep analysis, while "技术教程" videos get concise summaries.

---

## 🏗️ Architecture

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Nuxt 3 + Vue 3 + TypeScript | Reactive UI, file-based routing |
| **State** | Pinia | Centralized state management |
| **UI** | shadcn-vue + TailwindCSS | Accessible components, modern design |
| **Backend** | FastAPI + Python 3.12+ | Async API, type-safe |
| **Database** | SQLite + SQLAlchemy (async) | Local storage, zero-config |
| **Task Queue** | Huey | Background job processing |
| **AI** | External RPC Service | LLM calls, web scraping |

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐    │
│  │Dashboard│  │Collections│  │Workshops│  │ Settings │    │
│  └────┬────┘  └────┬─────┘  └────┬────┘  └────┬─────┘    │
│       │            │             │            │            │
│       └────────────┴─────────────┴────────────┘            │
│                         │                                   │
│                    API Client                               │
└─────────────────────────┼───────────────────────────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────┼───────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌──────────────────────┴────────────────────────────────┐ │
│  │                 API Endpoints                          │ │
│  └──────┬───────────────────────────────────────┬────────┘ │
│         │                                        │          │
│  ┌──────▼────────┐                       ┌──────▼────────┐ │
│  │   Services    │                       │ Stream Manager│ │
│  │  - Workshop   │◄──────────────────────│ - Monitor     │ │
│  │  - Favorites  │                       │ - Auto-trigger│ │
│  │  - Dashboard  │                       └───────────────┘ │
│  └──────┬────────┘                                         │
│         │                                                   │
│  ┌──────▼────────┐          ┌────────────────┐           │
│  │     CRUD      │◄─────────│  Task Queue    │           │
│  │  Repository   │          │     (Huey)     │           │
│  └──────┬────────┘          └────────────────┘           │
│         │                                                   │
│  ┌──────▼──────────────────────────────────────────────┐  │
│  │              SQLite Database (Local)                │  │
│  │  - favorites - workshops - tasks - results - tags  │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                    RPC Client
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  External RPC Service                        │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ LLM API      │  │ Web Scraper  │  │ Platform Auth   │  │
│  │ (Yuanbao)    │  │ (Bilibili/XHS│  │ (Cookie Mgmt)   │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Patterns

#### 1. Stream-Driven Automation

```python
# Continuous monitoring of external platforms
StreamManager
  ├─ BilibiliStream (monitors collections)
  ├─ XiaohongshuStream (monitors favorites)
  └─ EventOrchestrator
      ├─ Parse event
      ├─ Persist brief item
      ├─ Sync details
      └─ Create workshop task (auto)
```

#### 2. Workshop System

```python
# Pluggable AI processing pipelines
Workshop (template)
  ├─ workshop_id: "snapshot-insight"
  ├─ executor_type: "llm_chat"
  ├─ default_prompt: "Analyze deeply..."
  └─ platform_bindings: [
      {"platform": "bilibili", "collection_ids": [1, 2, 3]}
  ]

Task (execution instance)
  ├─ status: pending → in_progress → success/failure
  ├─ favorite_item_id: 123
  └─ workshop_id: "snapshot-insight"

Result (output)
  ├─ content: "# Deep Analysis\n..."
  ├─ task_id: 456
  └─ favorite_item_id: 123
```

#### 3. Smart Routing

```python
# Collection → Workshop mapping
if item.collection_id in workshop.platform_bindings:
    create_task(workshop_id, item_id)
else:
    fallback_to_default_workshop()
```

---

## 📖 Documentation

### API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/dashboard` | GET | Dashboard overview data |
| `/api/v1/collections` | GET | List favorite items (paginated) |
| `/api/v1/workshops` | GET | List available workshops |
| `/api/v1/workshops/{id}/execute` | POST | Trigger workshop on item |
| `/api/v1/tasks/{id}` | GET | Get task status |
| `/api/v1/sync/bilibili/collections` | POST | Sync Bilibili collections |
| `/api/v1/streams` | GET | List active monitoring streams |
| `/api/v1/settings` | GET/PUT | Manage application settings |

### Environment Variables

Create `backend/.env`:

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./mindecho.db

# External RPC Service
EAI_BASE_URL=http://127.0.0.1:8008
EAI_API_KEY=your_api_key_here

# LLM Configuration
YUANBAO_CONVERSATION_ID=your_conversation_id
YUANBAO_COOKIE_IDS=["cookie_id_1", "cookie_id_2"]

# Platform Authentication
BILIBILI_COOKIE_IDS=["bilibili_cookie_1"]
XIAOHONGSHU_COOKIE_IDS=["xhs_cookie_1"]

# Stream Configuration
BILIBILI_FAVORITES_STREAM_INTERVAL=10
XIAOHONGSHU_STREAM_INTERVAL=15
```

---

## 🎨 Screenshots

### Dashboard
*Real-time overview of your knowledge activities*
![Dashboard](docs/images/dashboard.png)

### Workshop Interface
*AI processing with side-by-side source and insights*
![Workshop](docs/images/workshop.png)

### Collections Management
*Organize and search your favorites*
![Collections](docs/images/collections.png)

---

## 🧪 Development

### Running Tests

```bash
# Backend tests
cd backend
pytest                              # Run all tests
pytest -v                           # Verbose output
pytest --cov=app --cov-report=html  # With coverage report
pytest tests/api/endpoints/         # Specific directory

# Frontend tests (if available)
cd frontend
npm run test
```

### Code Quality

```bash
# Backend linting
cd backend
ruff check .                        # Check for issues
ruff check . --fix                  # Auto-fix issues

# Type checking
mypy app/
```

### Database Management

```bash
# View database
cd backend
sqlite3 mindecho.db
.tables                             # List tables
.schema favorite_items              # View schema
SELECT * FROM tasks LIMIT 10;       # Query data
```

---

## 🛠️ Troubleshooting

### Common Issues

**Q: Backend won't start**
- Check Python version: `python --version` (must be 3.12+)
- Verify dependencies: `pip install -r requirements.txt`
- Check `.env` file exists with valid configuration

**Q: Frontend won't connect to backend**
- Ensure backend is running on port 8000
- Check CORS settings in `backend/app/main.py`
- Verify API URL in `frontend/app/lib/api.ts`

**Q: Workshops not auto-triggering**
- Verify stream is running: `GET /api/v1/streams`
- Check platform bindings in Settings → Listening Management
- Enable listening toggle for the workshop
- Review backend logs for errors

**Q: No AI results generated**
- Verify EAI_BASE_URL and EAI_API_KEY are set
- Check external RPC service is running
- Review task status: `GET /api/v1/tasks/{id}`
- Check backend logs for LLM errors

---

## 🗺️ Roadmap

### ✅ Phase 1: Foundation (Complete)
- [x] Basic collection sync
- [x] Workshop system
- [x] Auto-triggering
- [x] Multi-platform support (Bilibili, 小红书)
- [x] Smart routing

### 🚧 Phase 2: Intelligence (In Progress)
- [ ] Semantic linking engine
- [ ] Knowledge graph visualization
- [ ] Smart recommendations
- [ ] Cross-platform synthesis

### 📋 Phase 3: Expansion (Planned)
- [ ] More platform integrations (YouTube, Twitter, Podcasts)
- [ ] Export formats (Markdown, Anki, Notion)
- [ ] Workshop chaining (multi-step pipelines)
- [ ] Mobile app

### 🔮 Phase 4: Advanced (Future)
- [ ] Local LLM support (no external RPC)
- [ ] Knowledge gap detection
- [ ] Spaced repetition system
- [ ] Collaborative knowledge sharing

---

## 🤝 Contributing

MindEcho is currently in active development. Contributions are welcome!

### Development Principles

1. **Privacy-First**: Never send user data to external services
2. **Automation-First**: Reduce manual work wherever possible
3. **Quality-First**: No "good enough" — every detail matters
4. **Test-First**: All new features must have tests

### How to Contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with tests
4. Run tests and linters
5. Commit with clear messages: `git commit -m 'feat: add amazing feature'`
6. Push to your branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

---

## 📄 License

This project is currently **private** and for personal/internal use. Please contact the author for licensing inquiries.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **Nuxt** - Intuitive Vue framework
- **shadcn-vue** - Beautiful accessible components
- **SQLAlchemy** - Powerful ORM
- All open-source contributors

---

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/mindecho/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/mindecho/discussions)
- **Email**: your-email@example.com

---

<div align="center">

**Made with ❤️ for knowledge workers who refuse to forget**

*"Before you forget, MindEcho has already thought for you."*

[⬆ Back to Top](#mindecho-思维回响)

</div>
