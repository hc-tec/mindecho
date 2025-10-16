"""
Email Notifier

Sends notifications via email using SMTP.
"""

import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Optional
import markdown

from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.notifications.context import (
    NotificationContext,
    NotificationResult,
    NotificationStatus,
)

logger = get_logger(__name__)


class EmailNotifier:
    """
    Sends notification content via email.

    Supports:
    - Plain text and HTML emails
    - Image attachments (if rendered)
    - Configurable SMTP settings
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        to_email: Optional[str] = None,
        use_tls: bool = True,
        subject_template: str = "MindEcho: {title}",
    ):
        """
        Initialize email notifier.

        Args:
            smtp_host: SMTP server host (defaults to settings.SMTP_HOST)
            smtp_port: SMTP server port (defaults to settings.SMTP_PORT)
            smtp_user: SMTP username (defaults to settings.SMTP_USER)
            smtp_password: SMTP password (defaults to settings.SMTP_PASSWORD)
            from_email: Sender email address (defaults to settings.EMAIL_FROM)
            to_email: Recipient email address (defaults to settings.EMAIL_TO)
            use_tls: Whether to use TLS (default: True)
            subject_template: Email subject template with {title} placeholder
        """
        self.smtp_host = smtp_host or getattr(settings, "SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or getattr(settings, "SMTP_PORT", 587)
        self.smtp_user = smtp_user or getattr(settings, "SMTP_USER", None)
        self.smtp_password = smtp_password or getattr(settings, "SMTP_PASSWORD", None)
        self.from_email = from_email or getattr(settings, "EMAIL_FROM", self.smtp_user)
        self.to_email = to_email or getattr(settings, "EMAIL_TO", None)
        self.use_tls = use_tls
        self.subject_template = subject_template

    async def send(self, context: NotificationContext) -> NotificationResult:
        """
        Send notification via email.

        Args:
            context: Notification context

        Returns:
            NotificationResult with success/failure status
        """
        try:
            # Validate configuration
            if not self.to_email:
                raise ValueError("to_email is not configured")
            if not self.smtp_user or not self.smtp_password:
                raise ValueError("SMTP credentials are not configured")

            # Build email content
            msg = self._build_email(context)

            # Send email
            self._send_smtp(msg)

            logger.info(f"Email sent successfully to {self.to_email}")

            return NotificationResult(
                status=NotificationStatus.SUCCESS,
                notifier_type="email",
                sent_at=datetime.utcnow(),
                external_id=f"{self.to_email}:{datetime.utcnow().isoformat()}",
                metadata={
                    "to": self.to_email,
                    "subject": msg["Subject"],
                },
            )

        except Exception as e:
            error_msg = f"Failed to send email: {e}"
            logger.error(error_msg, exc_info=True)

            return NotificationResult(
                status=NotificationStatus.FAILED,
                notifier_type="email",
                sent_at=datetime.utcnow(),
                error_message=error_msg,
            )

    def _build_email(self, context: NotificationContext) -> MIMEMultipart:
        """Build email message with content and attachments."""
        msg = MIMEMultipart("related")

        # Set headers
        msg["From"] = self.from_email
        msg["To"] = self.to_email
        msg["Subject"] = self.subject_template.format(
            title=context.get_item_title()
        )

        # Build email body
        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)

        # Plain text version
        plain_text = self._build_plain_text(context)
        msg_alternative.attach(MIMEText(plain_text, "plain", "utf-8"))

        # HTML version (if formatted text available)
        if context.html_content or context.formatted_text:
            html_text = self._build_html(context)
            msg_alternative.attach(MIMEText(html_text, "html", "utf-8"))

        # Attach image if available
        if context.rendered_image_data:
            image = MIMEImage(context.rendered_image_data)
            image.add_header("Content-ID", "<result_image>")
            image.add_header("Content-Disposition", "inline", filename="result.png")
            msg.attach(image)

        return msg

    def _build_plain_text(self, context: NotificationContext) -> str:
        """Build plain text email content."""
        lines = [
            f"标题: {context.get_item_title()}",
            f"工坊: {context.workshop.name}",
            f"平台: {context.get_item_platform()}",
            "",
            "=" * 50,
            "",
            context.get_display_text(),
            "",
            "=" * 50,
            "",
            "由 MindEcho 自动生成",
            f"时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        return "\n".join(lines)

    def _build_html(self, context: NotificationContext) -> str:
        """Build HTML email content with proper Markdown rendering."""
        # Use pre-rendered HTML if available
        if context.html_content:
            base_html = context.html_content
        else:
            # Convert Markdown to HTML using markdown library
            text = context.get_display_text()

            # Configure markdown with useful extensions
            base_html = markdown.markdown(
                text,
                extensions=[
                    'extra',        # Tables, fenced code blocks, etc.
                    'nl2br',        # Newlines become <br>
                    'sane_lists',   # Better list handling
                    'codehilite',   # Code syntax highlighting
                ],
                extension_configs={
                    'codehilite': {
                        'css_class': 'highlight',
                        'noclasses': True,  # Use inline styles
                    }
                }
            )

        # Wrap in email template with comprehensive CSS
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: white;
            color: white;
            padding: 30px;
            border-radius: 10px 10px 0 0;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .meta {{
            background: #f7f7f7;
            padding: 15px;
            border-left: 4px solid #667eea;
            margin: 0;
        }}
        .content {{
            padding: 20px;
            background: white;
        }}
        .content h1 {{
            font-size: 28px;
            margin-top: 30px;
            margin-bottom: 15px;
            color: #2c3e50;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .content h2 {{
            font-size: 24px;
            margin-top: 25px;
            margin-bottom: 12px;
            color: #34495e;
        }}
        .content h3 {{
            font-size: 20px;
            margin-top: 20px;
            margin-bottom: 10px;
            color: #4a5568;
        }}
        .content p {{
            margin: 10px 0;
        }}
        .content strong {{
            font-weight: 600;
            color: #2c3e50;
        }}
        .content em {{
            font-style: italic;
            color: #555;
        }}
        .content code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 90%;
            color: #d73a49;
        }}
        .content pre {{
            background-color: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
            margin: 15px 0;
        }}
        .content pre code {{
            background-color: transparent;
            padding: 0;
            color: #24292e;
        }}
        .content ul, .content ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        .content li {{
            margin: 5px 0;
        }}
        .content blockquote {{
            border-left: 4px solid #dfe2e5;
            padding-left: 16px;
            margin: 15px 0;
            color: #6a737d;
            font-style: italic;
        }}
        .content table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        .content th, .content td {{
            border: 1px solid #dfe2e5;
            padding: 8px 12px;
            text-align: left;
        }}
        .content th {{
            background-color: #f6f8fa;
            font-weight: 600;
        }}
        .content a {{
            color: #667eea;
            text-decoration: none;
        }}
        .content a:hover {{
            text-decoration: underline;
        }}
        .content hr {{
            border: none;
            border-top: 2px solid #e1e4e8;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #eee;
            background: white;
            border-radius: 0 0 10px 10px;
        }}
        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 20px 0;
        }}
        /* Syntax highlighting */
        .highlight {{
            background: #f6f8fa;
            border-radius: 6px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{context.get_item_title()}</h1>
    </div>

    <div class="meta">
        <strong>工坊:</strong> {context.workshop.name}<br>
        <strong>平台:</strong> {context.get_item_platform()}<br>
        <strong>时间:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
    </div>

    <div class="content">
        {base_html}
    </div>

    {"<img src='cid:result_image' alt='Result Visualization'>" if context.rendered_image_data else ""}

    <div class="footer">
        由 MindEcho 自动生成 | <a href="https://github.com/hc-tec/mindecho">了解更多</a>
    </div>
</body>
</html>
"""
        return html

    def _send_smtp(self, msg: MIMEMultipart) -> None:
        """Send email via SMTP."""
        if self.use_tls:
            # Use TLS (port 587)
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
        else:
            # Use SSL (port 465) or plain
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)

        try:
            # Login
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)

            # Send email
            server.send_message(msg)

            logger.debug(f"SMTP send successful to {self.to_email}")

        finally:
            server.quit()
