"""
Tests for LocalStorageNotifier.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from app.services.notifications.context import NotificationContext, NotificationStatus
from app.services.notifications.notifiers.local_storage import LocalStorageNotifier


@pytest.fixture
def temp_notification_dir():
    """Create a temporary directory for notifications."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_local_storage_basic(mock_favorite_item, mock_workshop, sample_result_text, temp_notification_dir):
    """Test basic local storage notification."""
    notifier = LocalStorageNotifier(
        output_dir=temp_notification_dir,
        organize_by_date=False,
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
    assert result.notifier_type == "local_storage"
    assert result.external_id is not None

    # Check file was created
    temp_path = Path(temp_notification_dir)
    txt_files = list(temp_path.glob("*.txt"))
    assert len(txt_files) == 1

    # Verify content
    content = txt_files[0].read_text(encoding="utf-8")
    assert "关键洞察" in content


@pytest.mark.asyncio
async def test_local_storage_with_metadata(mock_favorite_item, mock_workshop, sample_result_text, temp_notification_dir):
    """Test local storage with metadata saving."""
    notifier = LocalStorageNotifier(
        output_dir=temp_notification_dir,
        organize_by_date=False,
        save_metadata=True,
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

    # Check metadata file was created
    temp_path = Path(temp_notification_dir)
    meta_files = list(temp_path.glob("*_meta.json"))
    assert len(meta_files) == 1

    # Verify metadata structure
    import json
    metadata = json.loads(meta_files[0].read_text(encoding="utf-8"))
    assert "notification" in metadata
    assert "source_item" in metadata
    assert "workshop" in metadata
    assert metadata["source_item"]["title"] == "Test Video Title"


@pytest.mark.asyncio
async def test_local_storage_with_image(mock_favorite_item, mock_workshop, sample_result_text, temp_notification_dir):
    """Test local storage with rendered image."""
    notifier = LocalStorageNotifier(
        output_dir=temp_notification_dir,
        organize_by_date=False,
        save_images=True,
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )
    context.formatted_text = sample_result_text
    # Simulate rendered image
    context.rendered_image_data = b"fake_png_data"
    context.metadata["image_format"] = "png"

    result = await notifier.send(context)

    assert result.status == NotificationStatus.SUCCESS

    # Check image file was created
    temp_path = Path(temp_notification_dir)
    png_files = list(temp_path.glob("*.png"))
    assert len(png_files) == 1

    # Verify image data
    image_data = png_files[0].read_bytes()
    assert image_data == b"fake_png_data"


@pytest.mark.asyncio
async def test_local_storage_organize_by_date(mock_favorite_item, mock_workshop, sample_result_text, temp_notification_dir):
    """Test local storage with date organization."""
    notifier = LocalStorageNotifier(
        output_dir=temp_notification_dir,
        organize_by_date=True,
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

    # Check date subdirectory was created
    temp_path = Path(temp_notification_dir)
    date_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
    assert len(date_dirs) == 1
    # Directory name should be YYYY-MM-DD format
    assert len(date_dirs[0].name) == 10  # e.g., "2025-01-15"


@pytest.mark.asyncio
async def test_local_storage_error_handling(mock_favorite_item, mock_workshop, sample_result_text):
    """Test local storage error handling with invalid directory."""
    # Use an invalid directory that cannot be created
    notifier = LocalStorageNotifier(
        output_dir="/invalid/path/that/does/not/exist/and/cannot/be/created",
        organize_by_date=False,
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )
    context.formatted_text = sample_result_text

    result = await notifier.send(context)

    # Should fail gracefully
    assert result.status == NotificationStatus.FAILED
    assert result.error_message is not None


@pytest.mark.asyncio
async def test_local_storage_result_metadata(mock_favorite_item, mock_workshop, sample_result_text, temp_notification_dir):
    """Test that result metadata includes file paths."""
    notifier = LocalStorageNotifier(
        output_dir=temp_notification_dir,
        organize_by_date=False,
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )
    context.formatted_text = sample_result_text

    result = await notifier.send(context)

    assert result.metadata is not None
    assert "text_path" in result.metadata
    assert result.metadata["text_path"].endswith(".txt")
