# 邮件通知配置指南

## 快速开始

### 1. 配置环境变量

在 `backend/.env` 文件中添加：

```bash
# SMTP服务器配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# 邮件发送配置
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

### 2. 注册EmailNotifier

在 `notification_service.py` 的 `initialize()` 方法中添加：

```python
from app.services.notifications.notifiers import EmailNotifier

# 在 initialize() 方法中添加
register_notifier("email", EmailNotifier())
```

### 3. 使用邮件通知

```python
# 创建包含邮件通知的pipeline
pipeline = NotificationPipeline(
    name="email_notification",
    processor_names=["text_formatter"],
    notifier_name="email",
)
```

## 常见邮箱SMTP配置

### Gmail

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password  # 需要生成应用专用密码
```

**生成Gmail应用密码：**
1. 访问 https://myaccount.google.com/security
2. 启用两步验证
3. 搜索"应用专用密码"
4. 生成一个新的应用密码用于MindEcho

### Outlook/Hotmail

```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your_email@outlook.com
SMTP_PASSWORD=your_password
```

### QQ邮箱

```bash
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_authorization_code  # QQ邮箱的授权码
```

**获取QQ邮箱授权码：**
1. 登录QQ邮箱
2. 设置 → 账户 → POP3/IMAP/SMTP服务
3. 开启服务并生成授权码

### 163邮箱

```bash
SMTP_HOST=smtp.163.com
SMTP_PORT=465  # 使用SSL
SMTP_USER=your_email@163.com
SMTP_PASSWORD=your_authorization_code  # 163的授权码
```

### 企业邮箱（自定义SMTP）

```bash
SMTP_HOST=smtp.your-company.com
SMTP_PORT=587
SMTP_USER=your_email@company.com
SMTP_PASSWORD=your_password
```

## 高级配置

### 自定义邮件主题

```python
notifier = EmailNotifier(
    subject_template="[MindEcho] {title} - 来自{workshop}工坊",
)
```

### SSL模式（端口465）

```python
notifier = EmailNotifier(
    smtp_port=465,
    use_tls=False,  # SSL模式不使用TLS
)
```

### 多收件人（暂不支持，需扩展）

当前版本仅支持单个收件人。如需多收件人，可以：
1. 创建多个EmailNotifier实例
2. 使用PipelineOrchestrator并发发送

## 邮件内容格式

EmailNotifier会自动生成精美的HTML邮件，包含：

### HTML版本（默认）
- 渐变色标题栏
- 元信息卡片（工坊、平台、时间）
- 格式化内容（支持markdown转HTML）
- 图片嵌入（如果ImageRenderer生成了图片）
- 底部品牌信息

### 纯文本版本（备选）
- 自动生成纯文本版本作为fallback
- 适用于不支持HTML的邮件客户端

## 完整示例

### 示例1：基础文本邮件

```python
from app.services.notifications.pipeline import NotificationPipeline
from app.services.notifications.notifiers import EmailNotifier
from app.services.notifications.processors import TextFormatterProcessor
from app.services.notifications.registry import register_processor, register_notifier

# 注册组件
register_processor("email_text_formatter", TextFormatterProcessor(
    output_format="html",
    add_header=True,
    add_footer=True,
))
register_notifier("email", EmailNotifier())

# 创建pipeline
pipeline = NotificationPipeline(
    name="email_simple",
    processor_names=["email_text_formatter"],
    notifier_name="email",
)
```

### 示例2：带图片的精美邮件

```python
from app.services.notifications.processors import ImageRendererProcessor

# 注册图片渲染器
register_processor("image_renderer", ImageRendererProcessor(
    style="minimal_card",
    size=(1080, 1920),
))

# 创建带图片的pipeline
pipeline = NotificationPipeline(
    name="email_with_image",
    processor_names=[
        "email_text_formatter",
        "image_renderer",  # 生成图片
    ],
    notifier_name="email",
)
```

### 示例3：多渠道通知（邮件+本地存储）

```python
from app.services.notifications.pipeline import PipelineOrchestrator

# 创建多个pipeline
email_pipeline = NotificationPipeline(
    name="email",
    processor_names=["email_text_formatter"],
    notifier_name="email",
)

local_pipeline = NotificationPipeline(
    name="local_backup",
    processor_names=["text_formatter"],
    notifier_name="local_storage",
)

# 使用Orchestrator并发执行
orchestrator = PipelineOrchestrator([email_pipeline, local_pipeline])
results = await orchestrator.execute_all(context, db)
```

## 故障排查

### 问题1: "SMTP credentials are not configured"

**原因**: 未配置SMTP用户名或密码

**解决**: 检查 `.env` 文件中的 `SMTP_USER` 和 `SMTP_PASSWORD`

### 问题2: "Authentication failed"

**原因**:
- 密码错误
- 未使用应用专用密码（Gmail）
- 未开启SMTP服务（QQ、163）

**解决**:
- Gmail: 生成应用专用密码
- QQ/163: 获取授权码
- 其他: 验证密码正确性

### 问题3: "Connection refused"

**原因**: SMTP服务器地址或端口错误

**解决**: 检查 `SMTP_HOST` 和 `SMTP_PORT` 配置

### 问题4: 邮件被标记为垃圾邮件

**原因**:
- 发件人信誉度低
- 缺少SPF/DKIM配置

**解决**:
- 使用可信的SMTP服务器
- 配置域名的SPF/DKIM记录（企业邮箱）
- 添加发件人到白名单

### 问题5: 图片不显示

**原因**:
- 邮件客户端默认不加载远程图片
- 图片嵌入失败

**解决**:
- EmailNotifier使用CID（Content-ID）内嵌图片，不依赖远程加载
- 检查 `context.rendered_image_data` 是否有值

## 测试邮件配置

使用以下代码测试邮件发送：

```python
import asyncio
from app.services.notifications.notifiers import EmailNotifier
from app.services.notifications.context import NotificationContext
from app.db.models import FavoriteItem, Workshop

async def test_email():
    notifier = EmailNotifier(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="your_email@gmail.com",
        smtp_password="your_app_password",
        to_email="recipient@example.com",
    )

    # 创建测试context
    context = NotificationContext(
        result_id=1,
        result_text="这是一封测试邮件",
        favorite_item=MagicMock(id=1, title="测试标题", platform="bilibili"),
        workshop=MagicMock(workshop_id="test", name="测试工坊"),
    )

    result = await notifier.send(context)
    print(f"Status: {result.status}")
    print(f"Message: {result.error_message if result.status == 'failed' else 'Success!'}")

# 运行测试
asyncio.run(test_email())
```

## 安全建议

1. **不要将密码提交到Git**: `.env` 文件已在 `.gitignore` 中
2. **使用应用专用密码**: 避免使用主密码
3. **定期更换密码**: 建议每3-6个月更换一次
4. **限制发送频率**: 避免被SMTP服务器封禁
5. **加密传输**: 始终使用TLS/SSL

## 性能优化

### 批量通知延迟

如果同时触发多个邮件通知，建议添加延迟：

```python
import asyncio

for context in contexts:
    result = await notifier.send(context)
    await asyncio.sleep(1)  # 避免触发SMTP限流
```

### 异步发送

EmailNotifier已实现为async函数，不会阻塞主流程。

## 未来扩展

- [ ] 支持多收件人（CC、BCC）
- [ ] 支持邮件模板引擎（Jinja2）
- [ ] 支持附件（PDF、Excel等）
- [ ] 支持邮件追踪（阅读回执）
- [ ] 支持批量发送队列
