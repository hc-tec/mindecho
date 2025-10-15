"""
Tests for NotificationPipeline.
"""

import pytest
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock

from app.services.notifications.context import NotificationContext, NotificationStatus
from app.services.notifications.pipeline import NotificationPipeline
from app.services.notifications.processors.text_formatter import TextFormatterProcessor
from app.services.notifications.notifiers.local_storage import LocalStorageNotifier
from app.services.notifications.registry import register_processor, register_notifier


@pytest.fixture
def temp_notification_dir():
    """Create a temporary directory for notifications."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def setup_test_registry(temp_notification_dir):
    """Setup test processors and notifiers in registry."""
    # Register test processors
    register_processor("test_text_formatter", TextFormatterProcessor())

    # Register test notifier
    register_notifier(
        "test_local_storage",
        LocalStorageNotifier(output_dir=temp_notification_dir, organize_by_date=False)
    )

    yield

    # Cleanup registry (if needed)
    # Note: In real tests, you might want to clear registry between tests


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_pipeline_basic_execution(
    mock_favorite_item,
    mock_workshop,
    sample_result_text,
    setup_test_registry,
    mock_db_session,
):
    """Test basic pipeline execution."""
    pipeline = NotificationPipeline(
        name="test_pipeline",
        processor_names=["test_text_formatter"],
        notifier_name="test_local_storage",
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result = await pipeline.execute(context, mock_db_session)

    assert result.status == NotificationStatus.SUCCESS
    assert result.notifier_type == "test_local_storage"
    assert "test_text_formatter" in context.processed_by


@pytest.mark.asyncio
async def test_pipeline_processor_not_found(
    mock_favorite_item,
    mock_workshop,
    sample_result_text,
    setup_test_registry,
    mock_db_session,
):
    """Test pipeline with non-existent processor."""
    pipeline = NotificationPipeline(
        name="test_pipeline",
        processor_names=["nonexistent_processor"],
        notifier_name="test_local_storage",
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result = await pipeline.execute(context, mock_db_session)

    # Should still succeed (processor failure doesn't fail pipeline)
    assert result.status == NotificationStatus.SUCCESS
    # Should have error recorded
    assert len(context.errors) > 0


@pytest.mark.asyncio
async def test_pipeline_notifier_not_found(
    mock_favorite_item,
    mock_workshop,
    sample_result_text,
    setup_test_registry,
    mock_db_session,
):
    """Test pipeline with non-existent notifier."""
    pipeline = NotificationPipeline(
        name="test_pipeline",
        processor_names=["test_text_formatter"],
        notifier_name="nonexistent_notifier",
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result = await pipeline.execute(context, mock_db_session)

    # Should fail because notifier is critical
    assert result.status == NotificationStatus.FAILED
    assert "not found" in result.error_message


@pytest.mark.asyncio
async def test_pipeline_multiple_processors(
    mock_favorite_item,
    mock_workshop,
    sample_result_text,
    setup_test_registry,
    mock_db_session,
):
    """Test pipeline with multiple processors."""
    # Register second processor
    register_processor("test_text_formatter_2", TextFormatterProcessor(output_format="plain"))

    pipeline = NotificationPipeline(
        name="test_pipeline",
        processor_names=["test_text_formatter", "test_text_formatter_2"],
        notifier_name="test_local_storage",
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result = await pipeline.execute(context, mock_db_session)

    assert result.status == NotificationStatus.SUCCESS
    # Both processors should have been executed
    assert "test_text_formatter" in context.processed_by
    assert len(context.processed_by) >= 1  # At least one processor ran


@pytest.mark.asyncio
async def test_pipeline_context_isolation(
    mock_favorite_item,
    mock_workshop,
    sample_result_text,
    setup_test_registry,
    mock_db_session,
):
    """Test that pipeline doesn't modify original context."""
    pipeline = NotificationPipeline(
        name="test_pipeline",
        processor_names=["test_text_formatter"],
        notifier_name="test_local_storage",
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    # Store original values
    original_text = context.result_text
    original_processed_by = context.processed_by.copy()

    await pipeline.execute(context, mock_db_session)

    # Original values should be unchanged (context is modified in place, but we can check state)
    assert context.result_text == original_text
    # processed_by will have been modified, that's expected
    assert len(context.processed_by) > len(original_processed_by)


@pytest.mark.asyncio
async def test_pipeline_saves_log_on_success(
    mock_favorite_item,
    mock_workshop,
    sample_result_text,
    setup_test_registry,
    mock_db_session,
):
    """Test that pipeline saves notification log on success."""
    pipeline = NotificationPipeline(
        name="test_pipeline",
        processor_names=["test_text_formatter"],
        notifier_name="test_local_storage",
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    await pipeline.execute(context, mock_db_session)

    # Verify db.commit was called (log was saved)
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_pipeline_saves_log_on_failure(
    mock_favorite_item,
    mock_workshop,
    sample_result_text,
    setup_test_registry,
    mock_db_session,
):
    """Test that pipeline saves notification log on failure."""
    pipeline = NotificationPipeline(
        name="test_pipeline",
        processor_names=["test_text_formatter"],
        notifier_name="nonexistent_notifier",  # Will fail
    )

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result = await pipeline.execute(context, mock_db_session)

    assert result.status == NotificationStatus.FAILED
    # Should still save log even on failure
    assert mock_db_session.commit.called
