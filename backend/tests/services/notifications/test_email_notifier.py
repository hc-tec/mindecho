"""
Tests for EmailNotifier.
"""

import pytest
from unittest.mock import MagicMock, patch, ANY

from app.services.notifications.context import NotificationContext, NotificationStatus
from app.services.notifications.notifiers.email_notifier import EmailNotifier


@pytest.fixture
def mock_smtp():
    """Mock SMTP server."""
    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server
        yield mock_server


@pytest.mark.asyncio
async def test_email_basic(mock_favorite_item, mock_workshop, sample_result_text, mock_smtp):
    """Test basic email sending."""
    notifier = EmailNotifier(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="test@example.com",
        smtp_password="test_password",
        from_email="test@example.com",
        to_email="recipient@example.com",
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )
    context.formatted_text = sample_result_text

    result = await notifier.send(context)

    assert result.status == NotificationStatus.SUCCESS
    assert result.notifier_type == "email"
    assert "recipient@example.com" in result.metadata["to"]

    # Verify SMTP was called
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("test@example.com", "test_password")
    mock_smtp.send_message.assert_called_once()
    mock_smtp.quit.assert_called_once()


@pytest.mark.asyncio
async def test_email_with_image(mock_favorite_item, mock_workshop, sample_result_text, mock_smtp):
    """Test email with image attachment."""
    notifier = EmailNotifier(
        smtp_user="test@example.com",
        smtp_password="test_password",
        to_email="recipient@example.com",
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )
    context.formatted_text = sample_result_text
    context.rendered_image_data = b"fake_png_data"

    result = await notifier.send(context)

    assert result.status == NotificationStatus.SUCCESS

    # Verify email was sent with attachment
    mock_smtp.send_message.assert_called_once()
    sent_message = mock_smtp.send_message.call_args[0][0]

    # Check message has image attachment
    assert sent_message.is_multipart()


@pytest.mark.asyncio
async def test_email_html_content(mock_favorite_item, mock_workshop, sample_result_text, mock_smtp):
    """Test email with HTML content."""
    notifier = EmailNotifier(
        smtp_user="test@example.com",
        smtp_password="test_password",
        to_email="recipient@example.com",
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )
    context.formatted_text = sample_result_text
    context.html_content = "<h1>Test HTML</h1><p>Content</p>"

    result = await notifier.send(context)

    assert result.status == NotificationStatus.SUCCESS

    # Verify HTML content was included
    sent_message = mock_smtp.send_message.call_args[0][0]
    message_str = sent_message.as_string()
    assert "text/html" in message_str


@pytest.mark.asyncio
async def test_email_custom_subject(mock_favorite_item, mock_workshop, sample_result_text, mock_smtp):
    """Test email with custom subject template."""
    notifier = EmailNotifier(
        smtp_user="test@example.com",
        smtp_password="test_password",
        to_email="recipient@example.com",
        subject_template="Workshop Result: {title}",
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )
    context.formatted_text = sample_result_text

    result = await notifier.send(context)

    assert result.status == NotificationStatus.SUCCESS
    assert "Workshop Result:" in result.metadata["subject"]
    assert "Test Video Title" in result.metadata["subject"]


@pytest.mark.asyncio
async def test_email_missing_config():
    """Test email with missing configuration."""
    notifier = EmailNotifier(
        smtp_user=None,  # Missing credentials
        smtp_password=None,
        to_email="recipient@example.com",
    )

    context = NotificationContext(
        result_id=1,
        result_text="test",
        favorite_item=MagicMock(id=1, title="Test", platform="bilibili"),
        workshop=MagicMock(workshop_id="test", name="Test"),
    )

    result = await notifier.send(context)

    assert result.status == NotificationStatus.FAILED
    assert "SMTP credentials" in result.error_message


@pytest.mark.asyncio
async def test_email_missing_recipient():
    """Test email with missing recipient."""
    notifier = EmailNotifier(
        smtp_user="test@example.com",
        smtp_password="test_password",
        to_email=None,  # Missing recipient
    )

    context = NotificationContext(
        result_id=1,
        result_text="test",
        favorite_item=MagicMock(id=1, title="Test", platform="bilibili"),
        workshop=MagicMock(workshop_id="test", name="Test"),
    )

    result = await notifier.send(context)

    assert result.status == NotificationStatus.FAILED
    assert "to_email is not configured" in result.error_message


@pytest.mark.asyncio
async def test_email_smtp_failure(mock_favorite_item, mock_workshop, sample_result_text):
    """Test email with SMTP connection failure."""
    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_smtp_class.side_effect = Exception("SMTP connection failed")

        notifier = EmailNotifier(
            smtp_user="test@example.com",
            smtp_password="test_password",
            to_email="recipient@example.com",
        )

        context = NotificationContext(
            result_id=1,
            result_text=sample_result_text,
            favorite_item=mock_favorite_item,
            workshop=mock_workshop,
        )

        result = await notifier.send(context)

        assert result.status == NotificationStatus.FAILED
        assert "SMTP connection failed" in result.error_message


@pytest.mark.asyncio
async def test_email_ssl_mode(mock_favorite_item, mock_workshop, sample_result_text):
    """Test email with SSL mode (port 465)."""
    with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server

        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=465,  # SSL port
            smtp_user="test@example.com",
            smtp_password="test_password",
            to_email="recipient@example.com",
            use_tls=False,
        )

        context = NotificationContext(
            result_id=1,
            result_text=sample_result_text,
            favorite_item=mock_favorite_item,
            workshop=mock_workshop,
        )

        result = await notifier.send(context)

        assert result.status == NotificationStatus.SUCCESS
        # Verify SSL was used instead of TLS
        mock_smtp_ssl.assert_called_once_with("smtp.example.com", 465)
        mock_server.starttls.assert_not_called()
