"""
Fixtures for notification system tests.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from app.db.models import FavoriteItem, Workshop, Author, PlatformEnum, ItemTypeEnum


@pytest.fixture
def mock_favorite_item():
    """Create a mock favorite item for testing."""
    author = Author(
        id=1,
        platform_user_id="test_user_123",
        platform=PlatformEnum.bilibili,
        username="Test Author",
        avatar_url="https://example.com/avatar.jpg",
    )

    item = FavoriteItem(
        id=1,
        platform_item_id="BV1234567890",
        platform=PlatformEnum.bilibili,
        item_type=ItemTypeEnum.video,
        title="Test Video Title",
        intro="Test video description",
        cover_url="https://example.com/cover.jpg",
        favorited_at=datetime(2025, 1, 1, 12, 0, 0),
        author_id=1,
        author=author,
        tags=[],
    )

    return item


@pytest.fixture
def mock_workshop():
    """Create a mock workshop for testing."""
    workshop = Workshop(
        id=1,
        workshop_id="test-workshop",
        name="Test Workshop",
        description="Test workshop description",
        default_prompt="Test prompt: {source}",
        default_model="test-model",
        executor_type="llm_chat",
    )

    return workshop


@pytest.fixture
def sample_result_text():
    """Sample workshop result text."""
    return """# 关键洞察

这是一个测试结果，包含以下要点：

1. **重点一**：这是第一个重点内容
2. **重点二**：这是第二个重点内容
3. **重点三**：这是第三个重点内容

## 结论

测试结论内容。
"""
