# SMTP 邮件通知配置指南

MindEcho 支持通过邮件发送工坊任务完成通知。本指南将帮助你配置 SMTP 邮件服务。

## 快速配置

### 1. 编辑 `.env` 文件

在 `backend/` 目录下创建或编辑 `.env` 文件，添加以下配置：

```bash
# SMTP 服务器配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# 邮件地址
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

### 2. 重启后端服务

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 3. 在前端启用邮件通知

1. 进入任意工坊页面（如 `/workshops/snapshot-insight`）
2. 点击右上角的"通知配置"按钮
3. 开启通知
4. 在"通知渠道"下拉框中选择"邮件通知"
5. 点击"保存配置"

完成！工坊任务完成后会自动发送邮件通知。

---

## 常见邮件服务商配置

### Gmail (推荐)

**步骤 1: 启用两步验证**
1. 访问 [Google 账户安全设置](https://myaccount.google.com/security)
2. 启用"两步验证"

**步骤 2: 生成应用专用密码**
1. 访问 [应用专用密码](https://myaccount.google.com/apppasswords)
2. 选择"邮件"和"其他设备"
3. 生成密码并复制

**配置示例：**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password  # 使用应用专用密码
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

---

### QQ 邮箱

**步骤 1: 开启 SMTP 服务**
1. 登录 QQ 邮箱
2. 设置 → 账户 → POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
3. 开启"IMAP/SMTP服务"
4. 生成授权码并保存

**配置示例：**
```bash
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_qq_number@qq.com
SMTP_PASSWORD=your_authorization_code  # 使用授权码，不是QQ密码
EMAIL_FROM=your_qq_number@qq.com
EMAIL_TO=recipient@example.com
```

---

### 163 邮箱

**步骤 1: 开启 SMTP 服务**
1. 登录 163 邮箱
2. 设置 → POP3/SMTP/IMAP
3. 开启"IMAP/SMTP服务"
4. 设置授权密码

**配置示例：**
```bash
SMTP_HOST=smtp.163.com
SMTP_PORT=465  # 注意：163使用465端口（SSL）
SMTP_USER=your_email@163.com
SMTP_PASSWORD=your_authorization_password  # 使用授权密码
EMAIL_FROM=your_email@163.com
EMAIL_TO=recipient@example.com
```

**注意：** 163 邮箱使用 SSL (端口 465)，EmailNotifier 会自动检测并使用正确的连接方式。

---

### Outlook / Hotmail

**配置示例：**
```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your_email@outlook.com
SMTP_PASSWORD=your_password  # 使用账户密码
EMAIL_FROM=your_email@outlook.com
EMAIL_TO=recipient@example.com
```

---

### 企业邮箱 / 自定义 SMTP

**配置示例：**
```bash
SMTP_HOST=smtp.your-company.com
SMTP_PORT=587  # 或 465 (SSL)
SMTP_USER=your_email@your-company.com
SMTP_PASSWORD=your_password
EMAIL_FROM=your_email@your-company.com
EMAIL_TO=recipient@example.com
```

**端口说明：**
- `587` - STARTTLS (推荐，EmailNotifier 默认使用)
- `465` - SSL/TLS (EmailNotifier 自动检测)
- `25` - 非加密 (不推荐)

---

## 配置参数说明

| 参数 | 说明 | 必填 | 默认值 |
|------|------|------|--------|
| `SMTP_HOST` | SMTP 服务器地址 | 否 | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP 服务器端口 | 否 | `587` |
| `SMTP_USER` | SMTP 用户名（通常是邮箱地址） | 是 | - |
| `SMTP_PASSWORD` | SMTP 密码或授权码 | 是 | - |
| `EMAIL_FROM` | 发件人邮箱地址 | 否 | 使用 `SMTP_USER` |
| `EMAIL_TO` | 收件人邮箱地址 | 是 | - |

---

## 邮件内容预览

发送的邮件包含以下内容：

**邮件主题：**
```
MindEcho: [收藏项标题]
```

**邮件正文：**
- 精美的渐变色标题卡片
- 工坊名称、平台、生成时间
- AI 生成的完整内容（Markdown 或 HTML 格式）
- 可选的渲染图片（如果启用了图片渲染）
- MindEcho 署名和链接

**支持的格式：**
- 纯文本版本（所有邮件客户端兼容）
- HTML 版本（支持样式和图片）

---

## 故障排查

### 问题 1: 邮件发送失败

**错误信息：** `Failed to send email: (535, b'5.7.8 Error: authentication failed')`

**解决方案：**
1. 检查 `SMTP_USER` 和 `SMTP_PASSWORD` 是否正确
2. 如果使用 Gmail/QQ/163，确认使用的是**应用专用密码/授权码**，而不是账户密码
3. 检查是否启用了两步验证（Gmail 需要）

---

### 问题 2: 连接超时

**错误信息：** `TimeoutError` 或 `Connection refused`

**解决方案：**
1. 检查 `SMTP_HOST` 和 `SMTP_PORT` 是否正确
2. 检查防火墙是否阻止了 SMTP 端口（587 或 465）
3. 尝试切换端口：587 ↔ 465

---

### 问题 3: 邮件被识别为垃圾邮件

**解决方案：**
1. 检查收件箱的垃圾邮件文件夹
2. 将发件人添加到联系人列表
3. 标记邮件为"非垃圾邮件"

---

### 问题 4: 通知未发送

**检查步骤：**
1. 确认工坊通知配置已启用：
   - 进入工坊页面 → 通知配置
   - 确认"启用通知"开关为开启状态
   - 确认"通知渠道"选择了"邮件通知"
2. 查看后端日志：
   ```bash
   cd backend
   # 检查日志输出
   ```
3. 检查 `.env` 文件是否在正确的位置（`backend/.env`）

---

## 安全建议

1. **不要将 `.env` 文件提交到 Git**
   - 已在 `.gitignore` 中排除
   - 敏感信息仅保存在本地

2. **使用应用专用密码**
   - Gmail: 使用应用专用密码，不要使用账户密码
   - QQ/163: 使用授权码，不要使用邮箱密码

3. **限制收件人**
   - 仅设置你信任的邮箱地址
   - 避免泄露通知内容

4. **定期更新密码**
   - 定期轮换应用专用密码
   - 如有泄露立即撤销并重新生成

---

## 高级配置

### 自定义邮件主题模板

邮件主题默认格式为 `MindEcho: {title}`，目前暂不支持自定义。

未来版本将在 `notifier_config` 中支持：
```json
{
  "subject_template": "【MindEcho】{workshop_name} - {title}"
}
```

### 发送给多个收件人

当前版本仅支持单个收件人。如需发送给多人，可以：
1. 使用邮箱的转发功能
2. 设置邮件别名/群组

未来版本将支持配置多个收件人。

---

## 测试配置

配置完成后，建议进行测试：

1. **手动触发工坊任务：**
   - 进入任意工坊页面
   - 选择一个收藏项
   - 点击"执行工坊"
   - 等待任务完成

2. **检查邮件：**
   - 查看收件箱（可能需要几秒钟）
   - 如果未收到，检查垃圾邮件文件夹
   - 检查后端日志是否有错误信息

3. **验证邮件内容：**
   - 确认邮件主题正确
   - 确认内容完整显示
   - 如果启用了图片渲染，确认图片正常加载

---

## 相关文档

- [通知系统架构](./NOTIFICATION_SYSTEM.md)
- [邮件通知指南](./EMAIL_NOTIFICATION_GUIDE.md)
- [MindEcho 主文档](../README.md)

---

**支持的邮件服务商：**
- ✅ Gmail (推荐)
- ✅ QQ 邮箱
- ✅ 163 邮箱
- ✅ Outlook / Hotmail
- ✅ 企业邮箱 (支持标准 SMTP)

**隐私保证：**
- 所有邮件通过你的 SMTP 服务器发送
- MindEcho 不会收集或上传任何邮箱凭证
- 完全本地化，符合 Privacy-First 原则
