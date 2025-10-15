# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product Vision

**MindEcho (思维回响)** is not just another information management tool—it is a **personal cognitive companion** designed to solve a fundamental contradiction of the digital age: we collect information at an unprecedented rate, yet forget it with equal efficiency. Digital favorites are becoming "information graveyards" rather than "inspiration goldmines."

### Core Mission
Transform passive information hoarding into active knowledge synthesis. MindEcho bridges the gap between external information chaos and internal knowledge systems through intelligent automation.

### Four Strategic Pillars

1. **Absolute Privacy & Data Sovereignty**
   - 100% local execution—no cloud processing, no data collection, no external access
   - Your data, your rules, your control
   - *"Your thoughts belong only to you."*

2. **Deep Automation & Proactive Intelligence**
   - Zero-intervention automation engine that works silently in the background
   - Proactive knowledge gap discovery—MindEcho thinks before you forget
   - *"Before you forget, MindEcho has already thought for you."*

3. **Connected Knowledge Network**
   - Automatic semantic linking of new content with your entire knowledge history
   - Transforms isolated notes into interconnected insights
   - *"Activate your entire knowledge base—let every collection echo through your mind."*

4. **All-in-One Workflow**
   - Multi-modal input (video, images, text) → AI processing (summary, analysis, synthesis) → Structured output (reports, cards)
   - Replaces 5-6 separate tools with one unified experience
   - *"From information noise to final product, in one step."*

### Competitive Positioning

MindEcho occupies a unique niche that competitors cannot reach:

- **vs Platform bots** (e.g., @机器人): Private, accumulative, multi-dimensional processing
- **vs Automation connectors** (Zapier, IFTTT): Processes content, not just data pipes; local-first architecture
- **vs Knowledge management** (Notion, Obsidian): Solves the "input bottleneck"; AI as native engine, not addon
- **vs Read-it-later** (Pocket, Instapaper): Active processing, not passive storage; prevents "never-read" syndrome

## Project Overview

**Technical Architecture**: Backend (FastAPI + SQLAlchemy async) + Frontend (Nuxt 3 + Pinia) + External RPC service for LLM/scraping.

**Philosophy**: Local-first, automation-first, privacy-first. Every architectural decision serves our four strategic pillars.

## Development Commands

### Backend (Python 3.12+)

```bash
# Navigate to backend
cd backend

# Install dependencies (requires Python 3.12+)
pip install -r requirements.txt

# Run development server (auto-reload enabled)
uvicorn app.main:app --reload --port 8000

# Run all tests
pytest

# Run specific test file
pytest tests/api/endpoints/test_workshops.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run single test function
pytest tests/api/endpoints/test_workshops.py::test_workshop_crud_and_executor_config_roundtrip -v
```

**Database**: SQLite with async driver (`aiosqlite`). Schema auto-created on startup via `Base.metadata.create_all` in development.

**Environment Variables**: Create `.env` in `backend/` with:
- `DATABASE_URL`: SQLite path (default: `sqlite+aiosqlite:///./mindecho1.db`)
- `EAI_BASE_URL`: RPC service endpoint (default: `http://127.0.0.1:8008`)
- `EAI_API_KEY`: RPC authentication key
- `YUANBAO_CONVERSATION_ID`: LLM conversation ID for workshop tasks
- `YUANBAO_COOKIE_IDS`: List of cookie IDs for LLM auth

### Frontend (Nuxt 3)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server (port 3001)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Generate static site
npm run generate
```

**Dev Server**: Runs on `http://localhost:3001` by default (configured in `nuxt.config.ts`).

## Code Architecture

### Backend Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, startup/shutdown lifecycle
│   ├── api/endpoints/       # REST API routes (collections, workshops, sync, streams, etc.)
│   ├── services/            # Business logic layer
│   │   ├── workshop_service.py       # Workshop task creation & execution
│   │   ├── stream_manager.py         # Long-running plugin stream manager
│   │   ├── stream_event_handler.py   # Event orchestration (parse → persist → sync → task)
│   │   ├── listener_service.py       # Stream event handler registration
│   │   ├── favorites_service.py      # Favorites sync from external platforms
│   │   └── executors.py              # Pluggable AI executors (LLM chat, future plugins)
│   ├── crud/                # Database access layer (follows Repository pattern)
│   ├── db/
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   └── base.py          # Database engine & session factory
│   ├── schemas/             # Pydantic schemas for request/response
│   └── core/
│       ├── config.py        # Settings loaded from environment
│       ├── logging_config.py
│       ├── runtime_config.py # In-memory category→workshop mapping
│       └── websocket_manager.py
├── client_sdk/              # RPC client for external AI/scraping service
├── tests/                   # pytest test suite
└── requirements.txt
```

### Frontend Structure

```
frontend/
├── app/
│   ├── components/
│   │   ├── dashboard/       # Dashboard widgets
│   │   ├── workshops/       # Workshop-specific UI (GenericWorkshop, InformationAlchemy, etc.)
│   │   ├── layout/          # Sidebar, navigation
│   │   └── ui/              # shadcn-vue UI components
│   ├── pages/               # Nuxt file-based routing
│   │   ├── index.vue        # Dashboard
│   │   ├── collections.vue  # Collections list
│   │   ├── collections/[id].vue
│   │   ├── inbox.vue        # Pending items
│   │   ├── workshops/[id].vue
│   │   └── settings.vue
│   ├── stores/              # Pinia state management
│   │   ├── collections.ts
│   │   └── workshops.ts
│   ├── lib/api.ts           # API client wrapper
│   └── types/api.ts         # TypeScript types
├── nuxt.config.ts
└── package.json
```

## Design Philosophy

When developing features for MindEcho, always align with these core principles:

### 1. Zero-Intervention Principle
- **Automation by default**: Features should work without user commands
- **Silent intelligence**: Processing happens in the background
- **Proactive, not reactive**: Anticipate needs, don't wait for requests
- **Example**: Stream listeners auto-trigger workshops when content is favorited

### 2. Privacy-First Architecture
- **Local execution**: All data processing must run locally
- **No external dependencies**: Never send user data to third-party services (except user-controlled RPC)
- **Data sovereignty**: Users own and control their data completely
- **Example**: SQLite database, local LLM inference via RPC client

### 3. Knowledge Network Thinking
- **Everything connects**: New content should link to existing knowledge
- **Semantic relationships**: Go beyond tags—understand meaning
- **Accumulative value**: Each addition enriches the entire system
- **Future goal**: Implement automatic semantic linking engine

### 4. Unified Workflow Priority
- **Multi-modal by design**: Support video, audio, images, text equally
- **End-to-end processing**: From collection to insight in one system
- **Minimize context switching**: Keep users in flow state
- **Example**: SourceTextBuilder assembles rich context from multiple sources

## Key Architectural Patterns

### 1. Stream-Driven Automation (Implements: Pillar #2 - Proactive Intelligence)

**Strategic Intent**: Enable zero-intervention automation by continuously monitoring external platforms and auto-triggering AI processing.

**Flow**: External platform event → Stream → Event handler → Auto-create workshop task

**Implementation**:
- `stream_manager.py`: Manages long-running RPC plugin streams using `EAIRPCClient.run_plugin_stream`
- `stream_event_handler.py`: Implements clean event orchestration with Protocol-based dependency injection:
  - `EventParser` → `ItemPersister` → `DetailsSyncer` → `TaskCreator`
  - Follows strict ordering: brief item creation → detail sync → task creation (only if details exist)
  - Each component is testable in isolation
- Category mapping: `settings.category_to_workshop` maps Bilibili collection categories to workshop IDs

**Example**: User favorites a video in "深度思考" collection → Stream event → Auto-triggers `snapshot-insight` workshop

**Privacy Note**: Stream processing runs entirely in the backend; no data leaves the local system.

### 2. Workshop System (Implements: Pillar #4 - All-in-One Workflow)

**Strategic Intent**: Enable multi-dimensional AI processing through composable, pluggable executors. Each workshop represents a different cognitive lens for analyzing content.

**Core Components**:
- **Workshop**: Template for AI analysis (stored in `workshops` table with `workshop_id`, `default_prompt`, `executor_type`)
- **Task**: Execution instance (tracks `pending/in_progress/success/failure` status)
- **Result**: AI-generated output linked to both Task and FavoriteItem
- **Executor**: Pluggable backend for task execution (currently `llm_chat` via `execute_llm_chat`)

**Workshop execution flow**:
1. Create Task record → `start_workshop_task()`
2. Background execution → `run_workshop_task()` (uses Huey for async task queue)
3. Build rich source text → `SourceTextBuilder` (title, intro, author, tags, video metadata, subtitles)
4. Execute via pluggable executor → `executor_registry.get(executor_type)`
5. Save Result → `crud_result.create_or_update()`

**Multi-modal source text construction** (Implements: Unified Workflow): Uses builder pattern to assemble rich context from:
- Basic info (title, intro)
- Author metadata
- Tags
- Video statistics (view/like/coin counts)
- Subtitles (first 100 lines, critical for content understanding)

**Design principle**: Each workshop is independent and composable. Users can chain multiple workshops to create custom cognitive pipelines (e.g., Summary → Deep Analysis → Action Items).

### 3. Data Sync Pipeline (Implements: Pillar #1 - Data Sovereignty)

**Strategic Intent**: Maintain complete local copies of all external data to ensure privacy and enable offline access. Users own their data permanently.

**External → Internal model transformation**:
- `favorites_service.py`: Transforms RPC responses into ORM models
- Idempotent sync: Uses `platform_item_id` as unique key to prevent duplicates
- Relationship handling: Auto-creates `Author` and `Collection` if missing

**Privacy-preserving sync flow**:
1. RPC client fetches data from external platforms using user credentials
2. Data is immediately transformed into local models
3. All processing happens locally—no external services involved
4. Users can disconnect from platforms and still access their data

**Sync endpoints**:
- `POST /api/v1/sync/bilibili/collections` → Sync collection list
- `POST /api/v1/sync/bilibili/collections/{id}/videos` → Sync video list in collection
- `POST /api/v1/sync/bilibili/videos/details` → Batch fetch video details (stats, subtitles, URLs)

**Design principle**: Once synced, data belongs to the user forever. Platform changes or API deprecation cannot break MindEcho.

### 4. CRUD Layer Conventions

- All database access goes through `crud/` modules (never raw ORM in services)
- Use `AsyncSession` everywhere (no sync SQLAlchemy)
- Relationships use `lazy="selectin"` for async compatibility
- CRUD methods follow pattern: `get()`, `get_multi()`, `create()`, `update()`, `delete()`

### 5. Testing Best Practices

- Use `pytest-asyncio` with `asyncio_mode = auto` (set in `pytest.ini`)
- Test fixtures in `conftest.py` provide `client` (AsyncClient) and `db_session`
- Mock external dependencies: `@patch("app.services.executors.execute_llm_chat")`
- Use `AsyncMock` for coroutines
- Test both success and error paths

## Important Conventions

### Backend

1. **No direct ORM queries in endpoints**: Always use CRUD layer (maintains data sovereignty)
2. **Explicit commits**: CRUD methods only flush; services/endpoints must `await db.commit()`
3. **Error handling**: Wrap external calls (RPC, LLM) in try/except, log with context
4. **Type hints**: All functions must have full type annotations
5. **Logging**: Use structured logging via `LogConfig.setup_logging()` (called in `main.py`)
6. **Stream event handling**: Follow Protocol pattern (see README architecture rules)
7. **Privacy-first development**:
   - Never send user data to external services without explicit user control
   - All AI processing must route through user-controlled RPC endpoint
   - Log user actions locally only—no telemetry to external servers
8. **Automation-first design**:
   - Prefer background tasks over manual triggers
   - Use stream listeners for continuous monitoring
   - Default to automatic processing unless user explicitly disables

### Frontend

1. **API calls**: Always use `app/lib/api.ts` wrapper (handles base URL, error formatting)
2. **State management**: Use Pinia stores for cross-component state
3. **Component naming**: PascalCase for components, kebab-case for files
4. **TypeScript**: Strict mode enabled (`typescript.strict: true` in `nuxt.config.ts`)

## Cursor Rules Integration

From `.cursor/rules/.cursorrules`:

1. **Modular design**: Separate files for models, services, controllers
2. **Configuration**: Use environment variables via `pydantic-settings`
3. **Error handling**: Rich context logging for debugging
4. **Testing**: Comprehensive pytest coverage
5. **Code style**: Use Ruff for linting (run `ruff check .` before commits)
6. **AI-friendly practices**:
   - Descriptive names (avoid abbreviations)
   - Type hints everywhere
   - Comments for complex logic
   - Rich error context

### Design Ethos (from .cursorrules)

MindEcho embodies a perfectionist, uncompromising design philosophy:

- **Challenge assumptions**: When users request features, dig deeper to understand the real need
- **Obsess over details**: 2px spacing differences matter—users feel unconscious friction
- **Multiple proposals**: Always offer safe, radical, and ideal solutions
- **Honest trade-offs**: Explain consequences clearly, even if uncomfortable
- **Refuse mediocrity**: "Good enough" is the enemy of exceptional

This applies to code architecture, UX design, and feature planning. Every detail should serve our strategic pillars.

## Common Workflows

### Add a new workshop

1. Create workshop via API:
   ```bash
   POST /api/v1/workshops/manage
   {
     "workshop_id": "new-workshop",
     "name": "New Workshop",
     "default_prompt": "Analyze this: {source}",
     "executor_type": "llm_chat"
   }
   ```

2. (Optional) Add custom executor in `backend/app/services/executors.py`:
   ```python
   async def execute_custom(ctx: ExecutionContext, *, prompt_template: str, model: Optional[str]) -> str:
       # Custom logic here
       pass

   executor_registry._executors["custom_type"] = execute_custom
   ```

3. Map to category in settings (for auto-triggering):
   ```bash
   PUT /api/v1/settings
   {
     "category_to_workshop": {
       "新类别": "new-workshop"
     }
   }
   ```

### Debug stream events

1. Check running streams: `GET /api/v1/streams`
2. View logs: `backend/` will show stream events in console
3. Test event handler: See `tests/services/test_listener_service.py` for examples
4. Manually trigger workshop: `POST /api/v1/workshops/{id}/execute`

### Add new platform support

1. Add enum to `backend/app/db/models.py`: `class PlatformEnum`
2. Create detail model (e.g., `XiaohongshuNoteDetail`)
3. Add sync service in `favorites_service.py`
4. Create endpoint in `api/endpoints/sync.py`
5. Update `stream_event_handler.py` for new platform events
6. Ensure all data remains local (Pillar #1: Privacy)
7. Enable automatic sync via streams (Pillar #2: Automation)

## When to Add vs When to Refuse

### Always Say Yes To:
- Features that increase automation (reduce user friction)
- Privacy-enhancing changes (local processing, encryption)
- Knowledge connection features (semantic links, recommendations)
- Multi-modal support (more content types)
- Performance optimizations that improve silent background processing

### Always Challenge:
- Features requiring cloud services or third-party APIs
- Manual, repetitive workflows (ask: "Can we automate this?")
- UI complexity that breaks flow state
- Features that fragment the unified workflow
- "Nice-to-have" polish that doesn't serve the four pillars

### Propose Alternatives For:
- User: "Add a manual export button" → You: "What if MindEcho auto-exported on schedule?"
- User: "Let me tag items manually" → You: "What if we auto-tagged based on content analysis?"
- User: "Add search filters" → You: "What if we proactively surfaced relevant content?"

The goal is always: **More intelligence, less interaction.**

## Critical Dependencies

- **Huey**: Task queue for async workshop execution (uses SQLite backend)
- **EAIRPCClient**: External RPC service for LLM calls and web scraping (in `client_sdk/`)
- **SQLAlchemy async**: Must use `AsyncSession`, avoid lazy loading
- **Pydantic**: Schema validation for all API I/O

## Future Roadmap (Aligned with Strategic Pillars)

### Pillar #3: Connected Knowledge Network (Priority: High)
- **Semantic linking engine**: Auto-connect new content with historical knowledge base
- **Knowledge graph visualization**: Show relationships between items
- **Smart recommendations**: "You might also want to review..."
- **Cross-platform knowledge synthesis**: Link Bilibili videos with XHS notes

### Pillar #2: Proactive Intelligence (Priority: Medium)
- **Knowledge gap detection**: Identify missing concepts in user's knowledge base
- **Periodic review suggestions**: Surface old content at optimal intervals (spaced repetition)
- **Trend detection**: Notify when multiple items share emerging themes

### Pillar #4: All-in-One Workflow (Priority: Medium)
- **More platform integrations**: YouTube, Twitter, Podcasts, RSS feeds
- **Export formats**: Markdown reports, Anki cards, Notion pages
- **Workshop chaining**: Automated multi-step processing pipelines

### Pillar #1: Data Sovereignty (Priority: Low - Already Strong)
- **Backup/restore system**: Export entire knowledge base
- **Data portability**: Import from other note-taking tools

## Known Limitations

- **Settings stored in-memory** (`runtime_config.py`) - production should use database/config service
- **Only Bilibili platform fully implemented** (XHS is placeholder) - violates "All-in-One" principle
- **No authentication/authorization layer** - acceptable for single-user local deployment
- **Stream auto-restart not implemented** - manual restart required after server reboot
- **Task queue (Huey) uses SQLite** - consider Redis for production if performance becomes bottleneck
- **Semantic linking not yet implemented** - current tagging is manual only (blocks Pillar #3)
- **No offline LLM support** - currently requires external RPC service (weakens Pillar #1)
