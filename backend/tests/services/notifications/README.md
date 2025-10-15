# 通知系统测试

## 运行所有通知系统测试

```bash
cd backend
pytest tests/services/notifications/ -v
```

## 运行特定测试文件

```bash
# 测试文本格式化
pytest tests/services/notifications/test_text_formatter.py -v

# 测试本地存储
pytest tests/services/notifications/test_local_storage_notifier.py -v

# 测试邮件通知
pytest tests/services/notifications/test_email_notifier.py -v

# 测试Pipeline
pytest tests/services/notifications/test_pipeline.py -v
```

## 运行特定测试用例

```bash
pytest tests/services/notifications/test_text_formatter.py::test_text_formatter_markdown_default -v
```

## 测试覆盖率

```bash
pytest tests/services/notifications/ --cov=app.services.notifications --cov-report=html
```

## 测试内容

### test_text_formatter.py
- ✅ 默认markdown格式化
- ✅ 纯文本格式化
- ✅ HTML格式化
- ✅ 长度截断
- ✅ 添加/不添加标题
- ✅ 添加页脚
- ✅ 错误处理

### test_local_storage_notifier.py
- ✅ 基本���件保存
- ✅ 保存元数据
- ✅ 保存图片
- ✅ 按日期组织文件
- ✅ 错误处理
- ✅ Result元数据验证

### test_email_notifier.py
- ✅ 基本邮件发送
- ✅ 带图片附件
- ✅ HTML内容格式
- ✅ 自定义邮件主题
- ✅ 配置缺失处理
- ✅ SMTP连接失败处理
- ✅ SSL模式（端口465）
- ✅ TLS模式（端口587）

### test_pipeline.py
- ✅ 基本Pipeline执行
- ✅ 处理器未找到
- ✅ 通知器未找到
- ✅ 多个处理器串联
- ✅ 上下文隔离
- ✅ 成功时保存日志
- ✅ 失败时保存日志

## 测试依赖

测试使用以下库：
- pytest
- pytest-asyncio
- unittest.mock

所有依赖已在 `requirements.txt` 中。
