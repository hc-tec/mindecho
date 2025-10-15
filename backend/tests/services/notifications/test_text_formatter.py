"""
Tests for TextFormatter Processor.
"""

import pytest

from app.services.notifications.context import NotificationContext
from app.services.notifications.processors.text_formatter import TextFormatterProcessor


@pytest.mark.asyncio
async def test_text_formatter_markdown_default(mock_favorite_item, mock_workshop, sample_result_text):
    """Test text formatter with markdown output (default)."""
    processor = TextFormatterProcessor()

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result_context = await processor.process(context)

    assert result_context.formatted_text is not None
    assert "Test Video Title" in result_context.formatted_text
    assert "Test Workshop" in result_context.formatted_text
    assert "text_formatter" in result_context.processed_by


@pytest.mark.asyncio
async def test_text_formatter_plain(mock_favorite_item, mock_workshop, sample_result_text):
    """Test text formatter with plain text output."""
    processor = TextFormatterProcessor(output_format="plain")

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result_context = await processor.process(context)

    assert result_context.formatted_text is not None
    # Plain text should not have markdown formatting
    assert "**" not in result_context.formatted_text
    assert "#" not in result_context.formatted_text
    assert "关键洞察" in result_context.formatted_text


@pytest.mark.asyncio
async def test_text_formatter_html(mock_favorite_item, mock_workshop, sample_result_text):
    """Test text formatter with HTML output."""
    processor = TextFormatterProcessor(output_format="html")

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result_context = await processor.process(context)

    assert result_context.formatted_text is not None
    # HTML should contain tags
    assert "<" in result_context.formatted_text
    assert ">" in result_context.formatted_text


@pytest.mark.asyncio
async def test_text_formatter_max_length(mock_favorite_item, mock_workshop, sample_result_text):
    """Test text formatter with max length truncation."""
    processor = TextFormatterProcessor(max_length=100)

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result_context = await processor.process(context)

    assert result_context.formatted_text is not None
    assert len(result_context.formatted_text) <= 100
    assert result_context.formatted_text.endswith("...")


@pytest.mark.asyncio
async def test_text_formatter_no_header(mock_favorite_item, mock_workshop, sample_result_text):
    """Test text formatter without header."""
    processor = TextFormatterProcessor(add_header=False)

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result_context = await processor.process(context)

    assert result_context.formatted_text is not None
    # Should not add title header
    assert result_context.formatted_text.startswith("#")  # Original content starts with #


@pytest.mark.asyncio
async def test_text_formatter_with_footer(mock_favorite_item, mock_workshop, sample_result_text):
    """Test text formatter with footer."""
    processor = TextFormatterProcessor(add_footer=True)

    context = NotificationContext(
        result_id=1,
        result_text=sample_result_text,
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    result_context = await processor.process(context)

    assert result_context.formatted_text is not None
    assert "MindEcho" in result_context.formatted_text
    assert result_context.formatted_text.endswith("生成")


@pytest.mark.asyncio
async def test_text_formatter_error_handling(mock_favorite_item, mock_workshop):
    """Test text formatter error handling."""
    processor = TextFormatterProcessor()

    # Create context with None text (edge case)
    context = NotificationContext(
        result_id=1,
        result_text=None,  # Invalid
        favorite_item=mock_favorite_item,
        workshop=mock_workshop,
    )

    # Should handle gracefully
    result_context = await processor.process(context)

    # Should have error but still produce output
    assert len(result_context.errors) > 0 or result_context.formatted_text is not None
