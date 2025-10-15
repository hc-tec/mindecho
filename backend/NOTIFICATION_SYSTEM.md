# MindEcho 通知系统

## 概述

通知系统采用**可组合的Pipeline架构**，自动在workshop结果生成后发送通知。

## 快速开始

系统已集成到WorkshopService，**无需额外配置**即可使用默认功能：

```python
# 系统会在workshop result创建后自动：
# 1. 格式化文本（添加标题、元数据）
# 2. 保存到本地 ./notifications/ 目录
# 3. 记录日志到 notification_logs 表
```

### 查看通知

默认保存位置：`backend/notifications/YYYY-MM-DD/`

每个通知包含3个文件：
- `*_result_*.txt` - 格式化后的文本内容
- `*_result_*_meta.json` - 元数据（来源、workshop信息）
- `*_result_*.png` - 渲染的图片（如果启用ImageRenderer）

## 架构设计

### 三层架构

```
Result创建 → Pipeline → Processors → Notifier → 数据库日志
```

1. **Processor层**（处理内容）
   - `TextFormatter`: 格式化文本
   - `ImageRenderer`: 调用EAI RPC渲染图片

2. **Notifier层**（发送通知）
   - `LocalStorageNotifier`: 保存到本地文件
   - `EmailNotifier`: 发送邮件通知（支持HTML+图片）
   - 未来：XiaohongshuNotifier, TelegramNotifier

3. **Log层**（审计追踪）
   - 所有通知记录到 `notification_logs` 表

## 自定义Pipeline

### 添加图片渲染

```python
from app.services.notifications.processors import ImageRendererProcessor
from app.services.notifications.registry import register_processor

# 注册图片渲染器
register_processor(
    "image_renderer",
    ImageRendererProcessor(
        style="minimal_card",  # 渲染样式
        size=(1080, 1920),     # 图片尺寸
    )
)

# 在pipeline中使用
pipeline = NotificationPipeline(
    name="fancy_local",
    processor_names=["text_formatter", "image_renderer"],
    notifier_name="local_storage",
)
```

### 创建自定义Processor

```python
from app.services.notifications.protocols import ResultProcessor
from app.services.notifications.context import NotificationContext

class MyCustomProcessor:
    async def process(self, context: NotificationContext) -> NotificationContext:
        # 处理逻辑
        context.formatted_text = "处理后的内容"
        context.mark_processed_by("my_custom_processor")
        return context

# 注册
register_processor("my_processor", MyCustomProcessor())
```

### 创建自定义Notifier

```python
from app.services.notifications.protocols import ResultNotifier
from app.services.notifications.context import NotificationResult, NotificationStatus
from datetime import datetime

class MyCustomNotifier:
    async def send(self, context: NotificationContext) -> NotificationResult:
        # 发送逻辑
        try:
            # ... 发送到外部平台 ...
            return NotificationResult(
                status=NotificationStatus.SUCCESS,
                notifier_type="my_notifier",
                sent_at=datetime.utcnow(),
                external_id="platform_message_id",
            )
        except Exception as e:
            return NotificationResult(
                status=NotificationStatus.FAILED,
                notifier_type="my_notifier",
                sent_at=datetime.utcnow(),
                error_message=str(e),
            )

# 注册
register_notifier("my_notifier", MyCustomNotifier())
```

## 配置邮件通知

详细配置指南见：[EMAIL_NOTIFICATION_GUIDE.md](./EMAIL_NOTIFICATION_GUIDE.md)

### 快速配置

```bash
# .env
# SMTP配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# 收件人
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

### 启用邮件通知

```python
from app.services.notifications.notifiers import EmailNotifier
from app.services.notifications.registry import register_notifier

# 在notification_service.initialize()中添加
register_notifier("email", EmailNotifier())

# 创建邮件通知pipeline
pipeline = NotificationPipeline(
    name="email_notification",
    processor_names=["text_formatter"],
    notifier_name="email",
)
```

## EAI RPC集成

ImageRenderer通过EAI RPC服务渲染图片，需要配置：

```bash
# .env
EAI_BASE_URL=http://127.0.0.1:8008
EAI_API_KEY=your_api_key
```

RPC调用：`client.render_image(content, title, style, size, metadata)`

## 数据库

### notification_logs表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| result_id | Integer | 关联的Result ID |
| pipeline_name | String | Pipeline名称 |
| notifier_type | String | Notifier类型 |
| status | Enum | pending/success/failed/retrying |
| content_snapshot | Text | 内容快照（1000字符） |
| error_message | Text | 错误信息 |
| external_id | String | 外部平台ID |
| created_at | DateTime | 创建时间 |
| sent_at | DateTime | 发送时间 |

### 查询通知历史

```python
from app.crud import notification_log

# 查询某个result的所有通知
logs = await notification_log.get_by_result_id(db, result_id=123)

# 查询失败的通知
failed = await notification_log.get_failed_logs(db, limit=50)
```

## 文件结构

```
backend/app/services/notifications/
├── __init__.py                 # 导出接口
├── protocols.py                # Protocol定义（ResultProcessor, ResultNotifier）
├── context.py                  # 上下文数据结构（NotificationContext, NotificationResult）
├── registry.py                 # 插件注册表
├── pipeline.py                 # Pipeline编排器
├── notification_service.py     # 高层服务接口
├── processors/
│   ├── text_formatter.py       # 文本格式化
│   └── image_renderer.py       # 图片渲染（调用EAI RPC）
└── notifiers/
    └── local_storage.py        # 本地存储

backend/app/crud/
└── crud_notification_log.py    # 通知日志CRUD

backend/app/db/models.py
└── NotificationLog             # 通知日志模型
```

## 未来扩展

### Phase 2: 小红书集成

```python
class XiaohongshuNotifier:
    async def send(self, context: NotificationContext):
        # 1. 上传图片到小红书
        # 2. 创建笔记（草稿或发布）
        # 3. 返回笔记ID
        pass
```

### Phase 3: 多渠道并发

```python
orchestrator = PipelineOrchestrator(pipelines=[
    NotificationPipeline("xiaohongshu", [...], "xiaohongshu"),
    NotificationPipeline("email", [...], "email"),
    NotificationPipeline("telegram", [...], "telegram"),
])

results = await orchestrator.execute_all(context, db)
```

### Phase 4: 配置化

通过前端UI配置pipeline，存储到settings表：

```json
{
  "notification_pipelines": [
    {
      "name": "xiaohongshu_card",
      "enabled": true,
      "trigger": {"workshop_ids": ["snapshot-insight"]},
      "processors": ["text_formatter", "image_renderer"],
      "notifier": "xiaohongshu"
    }
  ]
}
```

## 故障排查

### 通知没有发送

1. 检查系统是否初始化：`notification_service.initialize()` 已在 `main.py` startup调用
2. 查看日志：`grep "Notification" backend/*.log`
3. 检查notification_logs表：是否有FAILED状态记录

### 图片渲染失败

1. 检查EAI RPC服务是否运行
2. 验证.env配置：`EAI_BASE_URL`, `EAI_API_KEY`
3. 查看错误日志：`context.errors` 或 `notification_logs.error_message`

### 本地文件未生成

1. 检查目录权限：`backend/notifications/` 是否可写
2. 查看LocalStorageNotifier日志
3. 验证NotificationContext是否正确构建

## 示例代码

完整示例见：`backend/tests/services/test_notifications.py`（待添加）

## 设计文档

- CLAUDE.md - 项目整体架构
- 本文档 - 通知系统详细说明
