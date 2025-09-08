## MindEcho 后端（功能说明）

MindEcho 是一个面向“跨平台收藏与 AI 助理”的聚合与加工系统。后端基于 FastAPI 构建，负责：

- 聚合外部平台（目前以 B 站为主）的收藏夹与内容元数据
- 管理收藏条目、标签、集合与作者信息
- 触发并跟踪 AI 工作坊（Workshop）任务，生成洞察/摘要等结果
- 提供全局搜索、仪表盘汇总、设置管理和 LLM 代理访问
- 通过 WebSocket 推送长任务的实时进度与增量输出

### 核心业务优先级（自动触发）
- 当用户在外部平台点击“收藏”后，后端通过流式监听（Streams）自动感知新增收藏，并按照收藏夹类别自动选择并执行相应的工作坊任务（如：深度思考、精简摘要）。
- 手动在前端触发任务是补充能力，但非核心路径。

### 系统角色与边界
- **数据接入层**：通过 `client_sdk` 与外部抓取/处理服务通信，获取收藏集合、视频清单与详情。
- **数据管理层**：统一落库为本地模型（作者、集合、收藏条目、媒体详情、标签等）。
- **AI 任务层**：定义“工作坊（Workshop）”概念，发起、异步执行、保存结果，并对结果进行再生与编辑。
- **服务接口层**：提供 RESTful API 与 WebSocket 以支撑前端应用。


## 主要功能

### 1) 仪表盘总览（Dashboard）
- 汇总数据：概览统计、活动热力图、待处理队列、工作坊矩阵、近期输出、趋势（标签）
- 一次请求返回整页渲染所需的聚合数据
- API：`GET /api/v1/dashboard`

### 2) 收藏管理（Collections / Favorite Items）
- 列表分页、排序、按标签过滤
- 收件箱视图（仅显示 `pending` 状态条目）
- 单条详情查询
- 手动创建/编辑/删除收藏条目
- 为条目增删标签
- API 根：`/api/v1/collections`
  - `GET /`：分页列表（可按 `tags`、`sort_by`、`sort_order` 过滤/排序）
  - `GET /inbox`：待处理队列
  - `GET /{id}`：详情
  - `POST /`：创建
  - `PUT /{id}`：更新
  - `DELETE /{id}`：删除
  - `POST /{id}/tags`、`DELETE /{id}/tags`：标签维护

### 3) 标签（Tags）
- 返回所有标签及使用次数，用于筛选/趋势
- API：`GET /api/v1/tags`

### 4) 数据同步（Sync / Bilibili）
- 同步收藏夹列表
- 同步指定收藏夹内的视频清单（brief）
- 批量拉取视频详情（统计、分辨率、音视频直链、字幕、分类、标签等）
- 均通过 `client_sdk` 与外部 RPC 服务通信，并转换/落库为本地统一模型
- API：
  - `POST /api/v1/sync/bilibili/collections`：同步收藏夹列表
  - `POST /api/v1/sync/bilibili/collections/{platform_collection_id}/videos`：同步该收藏夹下视频清单
  - `POST /api/v1/sync/bilibili/videos/details`：按 `bvid` 列表批量更新详情

### 5) 流式监听与自动任务（Streams → Workshops）
- 基于 `client_sdk.run_plugin_stream` 的长连接拉流能力，对指定收藏夹或账号进行持续监听
- 后端 `stream_manager` 将流事件广播到 Web 前端，同时触发内部事件处理器，将“新增收藏”等事件映射为对应工作坊任务并自动执行
- API：
  - `GET /api/v1/streams`：列出运行中的流
  - `POST /api/v1/streams/start`：启动监听流（参数包括 `plugin_id`、`run_mode`、`interval`、`buffer_size`、`params` 等）
  - `POST /api/v1/streams/{stream_id}/stop`：停止流
  - `WS /api/v1/ws/streams/{stream_id}`：订阅该流的原始事件
- 事件格式（示例）：
  - `{"type":"favorite_added","platform":"bilibili","collection_id":"...","item":{"bvid":"BV...","category":"精简摘要", ...}}`
- 类别映射（默认示例）：
  - `精简摘要` → `summary-01`
  - `深度思考` → `snapshot-insight`
  - 未匹配时回退到 `summary-01`

### 5) 搜索（Search）
- 全局搜索收藏条目（标题、简介）与 AI 结果（内容），统一返回
- API：`GET /api/v1/search?q=...`

### 6) AI 工作坊（Workshops）与任务（Tasks）
- 预置多类工作坊：如“精华摘要”“快照洞察”“信息炼金术”“观点对撞”“学习任务”
- 自动/手动发起工作坊任务，后台异步执行，返回 `task_id`
- 通过 WebSocket 推送任务状态与流式 token，实现前端实时渲染
- 任务状态总览、单任务状态查询、清理已完成任务
- API：
  - `GET /api/v1/workshops`：列出可用工作坊
  - `POST /api/v1/workshops/{workshop_id}/execute`：对指定收藏条目执行工作坊（返回 `task_id`）
  - `WS /api/v1/workshops/ws/{task_id}`：订阅任务流式进度
  - `GET /api/v1/tasks/status`：全局任务统计
  - `GET /api/v1/tasks/{task_id}`：单任务状态
  - `DELETE /api/v1/tasks/clear-completed`：清理成功/失败任务

### 7) 结果管理（Results）
- AI 生成结果的增删改
- 支持“再生”结果：为结果所在条目新建并运行工作坊任务，完毕后回写该结果或新建结果
- API：
  - `PUT /api/v1/results/{id}`：修改内容
  - `DELETE /api/v1/results/{id}`：删除
  - `POST /api/v1/results/{id}/regenerate`：再生（返回触发的 `task`）

### 8) 设置（Settings）
- 获取与更新应用设置（如主题、通知、AI 模型等）
- API：
  - `GET /api/v1/settings`
  - `PUT /api/v1/settings`
  - 运行时映射：`category_to_workshop`（字典）支持动态配置“收藏夹类别→工作坊”映射，无需重启。例如：
    ```json
    {
      "theme": "dark",
      "notifications_enabled": true,
      "ai_model": "gemini-2.5-flash-preview-05-20",
      "category_to_workshop": {
        "精简摘要": "summary-01",
        "深度思考": "snapshot-insight",
        "信息炼金术": "information-alchemy"
      }
    }
    ```

### 9) LLM 代理（LLM Proxy）
- 将前端请求安全转发给后端的 `client_sdk`（示例使用 `EAIRPCClient`）
- API：`POST /api/v1/llm/call`


## 数据模型（简述）
- `Author`：作者（平台用户）
- `Collection`：外部平台的收藏夹/合集
- `FavoriteItem`：收藏条目（视频/笔记等），关联作者、集合、标签，持久化发布时间、收藏时间、封面、简介与状态
- `BilibiliVideoDetail`：B 站视频详情（统计、分辨率、分类、弹幕数等），并挂载 `BilibiliVideoUrl`、`BilibiliAudioUrl`、`BilibiliSubtitle`
- `Tag`：标签，多对多关联收藏条目
- `Result`：工作坊的 AI 产出，关联收藏条目与触发的 `Task`
- `Task`：工作坊任务（`pending/in_progress/success/failure`），关联收藏条目与产出


## 典型工作流

### A. 首次接入与落库
1. 同步收藏夹列表 → `POST /sync/bilibili/collections`
2. 选择一个收藏夹，同步视频清单 → `POST /sync/bilibili/collections/{id}/videos`
3. 批量补充视频详情 → `POST /sync/bilibili/videos/details`

### B. 自动加工与消费
1. 启动监听流 → `POST /streams/start`（指定 `plugin_id` 与参数：被监听的收藏夹/账号）
2. 用户在外部平台点击“收藏”
3. 流事件抵达后端并广播；事件处理器按类别选择工作坊并自动创建任务
4. 前端通过 `WS /workshops/ws/{task_id}` 实时接收进度与流式 token
5. 结果入库后，可在结果页编辑或再生 → `PUT /results/{id}` / `POST /results/{id}/regenerate`

### C. 日常管理
- 收藏条目增删改、打标签、过滤/搜索
- 清理已完成任务，维护设置


## 接口分组与路由前缀
- 基础根路由：`GET /` → 健康欢迎信息
- 统一前缀：`/api/v1`
  - Dashboard：`/dashboard`
  - Collections：`/collections/...`
  - Tags：`/tags`
  - Results：`/results/...`
  - Tasks：`/tasks/...`
  - Workshops：`/workshops/...` 与 `/workshops/ws/{task_id}`
  - Search：`/search`
  - LLM：`/llm/call`
  - Settings：`/settings`
  - Sync：`/sync/bilibili/...`


## 运行与开发（简要）
- 环境：Python 3.10+；建议使用虚拟环境
- 依赖：参见 `backend/requirements.txt`
- 启动：
  - 创建/迁移数据库由应用启动时自动建表（开发环境）
  - 运行后端（示例）：`python backend/run_server.py` 或使用 `uvicorn app.main:app --reload`
  - 某些同步/工作坊能力依赖本地运行的 RPC 服务（由 `EAI_BASE_URL`/`EAI_API_KEY` 配置）

### 任务实现最佳实践（LLM）
- 统一通过 `client_sdk` 的 `chat_with_yuanbao` 与大模型通信，后端在任务执行中：
  - 按 `workshop_id` 选择合适的系统提示/提示模板
  - 从 `FavoriteItem` 提取上下文（标题、简介，或将来接入全文/字幕）
  - 调用模型获取结果，并通过 WebSocket 推送增量/最终文本给前端
- 配置项：在 `backend/app/core/config.py` 中通过环境变量设置 `EAI_BASE_URL` 与 `EAI_API_KEY`
- 流式监听触发：在应用启动时注册事件处理器，将 `favorite_added` 事件映射为对应工作坊并自动执行


## 安全与日志
- 统一接入 `LogConfig`，应用启动时初始化日志
- LLM/同步接口对异常进行捕获并转译为合理的 HTTP 错误
- 与外部服务通信失败时，日志保留上下文，便于排查


## 面向前端的契约要点
- 返回模型均为 Pydantic Schema，字段命名稳定
- 列表接口返回 `{ total, items }` 便于分页
- WebSocket 事件：
  - 状态变更：`{"status": "in_progress" | "success" | "failure"}`
  - 流式 token：`{"type": "token", "data": "..."}`
  - 完成事件包含 `result` 文本


## 目录导航（后端）
- `backend/app/main.py`：应用入口与路由挂载
- `backend/app/api/endpoints/*`：REST/WS 接口
- `backend/app/services/*`：业务编排（仪表盘、收藏同步、工作坊）
- `backend/app/crud/*`：数据库访问层
- `backend/app/db/models.py`：ORM 模型
- `backend/app/schemas/unified.py`：统一返回/请求模型
- `backend/app/core/*`：配置、日志、WebSocket 管理
- `backend/client_sdk/*`：RPC 客户端与参数封装（示例）


## 已知限制
- 当前示例实现以 B 站为主，XHS 等平台为预留
- LLM 与同步能力依赖本地 RPC 服务（需保证对应服务可用）
- Settings 为内存示例实现，生产可改为数据库/配置中心


## 许可
本项目默认为内部示例/私有用途，若需开源许可请在此处补充说明。


