"""
Tests for Xiaohongshu Stream Event Handler.

Verifies the complete flow:
1. Event parsing
2. Brief item persistence
3. Details syncing with retry mechanism
4. Task creation (only after successful details fetch)
"""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from app.db.models import (
    FavoriteItem, Collection, Author, Workshop as WorkshopModel,
    PlatformEnum, ItemTypeEnum, XiaohongshuNoteDetail
)
from app.services.xiaohongshu_event_handler import (
    create_xiaohongshu_event_orchestrator,
    DefaultXiaohongshuEventParser,
    XiaohongshuStreamEventData,
    XiaohongshuNoteItemBrief,
    XiaohongshuCreatorInfo
)


@pytest.fixture
def sample_xiaohongshu_event():
    """Sample Xiaohongshu stream event with added items."""
    return {
        "plugin_id": "xiaohongshu_favorites",
        "topic_id": "xiaohongshu-test",
        "payload": {
            "result": {
                "success": True,
                "data": {
                    "added": {
                        "data": [
                            {
                                "id": "note123",
                                "note_id": "note123",
                                "xsec_token": "xsec_token_123",
                                "collection_id": "xhs_col_1",
                                "title": "测试小红书笔记",
                                "cover_image": "https://example.com/cover.jpg",
                                "author_info": {
                                    "user_id": "user456",
                                    "username": "测试用户",
                                    "avatar": "https://example.com/avatar.jpg"
                                },
                                "fav_time": "1704067200",  # 2024-01-01
                                "statistic": {
                                    "like_count": 100,
                                    "collect_count": 50,
                                    "comment_count": 20,
                                    "share_count": 10
                                }
                            }
                        ]
                    }
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_xiaohongshu_event_parser():
    """Test that Xiaohongshu events are correctly parsed."""
    parser = DefaultXiaohongshuEventParser()

    event = {
        "payload": {
            "result": {
                "success": True,
                "data": {
                    "added": {
                        "data": [
                            {
                                "id": "note123",
                                "note_id": "note123",
                                "xsec_token": "token",
                                "collection_id": "col1",
                                "title": "Test Note",
                                "cover_image": "cover.jpg",
                                "author_info": {
                                    "user_id": "user1",
                                    "username": "User",
                                    "avatar": "avatar.jpg"
                                },
                                "fav_time": "1704067200"
                            }
                        ]
                    }
                }
            }
        }
    }

    result = await parser.parse(event)

    assert isinstance(result, XiaohongshuStreamEventData)
    assert len(result.items) == 1

    note = result.items[0]
    assert isinstance(note, XiaohongshuNoteItemBrief)
    assert note.note_id == "note123"
    assert note.xsec_token == "token"
    assert note.title == "Test Note"
    assert note.creator.user_id == "user1"


@pytest.mark.asyncio
async def test_xiaohongshu_brief_item_persistence(db_session, sample_xiaohongshu_event):
    """Test that brief Xiaohongshu notes are correctly persisted to database."""
    # Create collection first
    author = Author(
        platform_user_id="user456",
        platform=PlatformEnum.xiaohongshu,
        username="测试用户",
        avatar_url="https://example.com/avatar.jpg"
    )
    db_session.add(author)
    await db_session.commit()
    await db_session.refresh(author)

    collection = Collection(
        platform_collection_id="xhs_col_1",
        platform=PlatformEnum.xiaohongshu,
        title="测试收藏夹",
        author_id=author.id,
        item_count=0
    )
    db_session.add(collection)
    await db_session.commit()
    await db_session.refresh(collection)

    # Create orchestrator and handle event
    orchestrator = create_xiaohongshu_event_orchestrator()

    # Mock the details syncer to avoid actual RPC calls
    with patch.object(orchestrator.syncer, 'sync_details', new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = []  # No items with details yet

        # Mock task creator to avoid task creation
        with patch.object(orchestrator.task_creator, 'create_analysis_tasks', new_callable=AsyncMock):
            await orchestrator.handle_event(sample_xiaohongshu_event, db_session)

    # Verify item was created
    result = await db_session.execute(
        select(FavoriteItem).where(FavoriteItem.platform_item_id == "note123")
    )
    db_item = result.scalars().first()

    assert db_item is not None
    assert db_item.platform == PlatformEnum.xiaohongshu
    assert db_item.item_type == ItemTypeEnum.note
    assert db_item.title == "测试小红书笔记"
    assert db_item.cover_url == "https://example.com/cover.jpg"
    assert db_item.collection_id == "xhs_col_1"


@pytest.mark.asyncio
async def test_xiaohongshu_retry_mechanism(db_session):
    """Test that the retry mechanism correctly tracks attempts and respects limits."""
    # Create author and item
    author = Author(
        platform_user_id="user789",
        platform=PlatformEnum.xiaohongshu,
        username="测试用户",
        avatar_url="avatar.jpg"
    )
    db_session.add(author)
    await db_session.commit()
    await db_session.refresh(author)

    # Create a note without details
    item = FavoriteItem(
        platform_item_id="note_retry_test",
        platform=PlatformEnum.xiaohongshu,
        item_type=ItemTypeEnum.note,
        title="Retry Test Note",
        intro="",
        cover_url="cover.jpg",
        favorited_at=datetime.utcnow(),
        author_id=author.id,
        details_fetch_attempts=0
    )
    db_session.add(item)

    # Create minimal XiaohongshuNoteDetail with xsec_token
    note_detail = XiaohongshuNoteDetail(
        favorite_item_id=item.id,
        note_id="note_retry_test",
        xsec_token="xsec_token_retry",
        desc="",  # Empty desc means details not fetched
        ip_location="",
        published_date=""
    )
    db_session.add(note_detail)
    await db_session.commit()
    await db_session.refresh(item)

    # Mock the favorites_service.sync_xiaohongshu_note_details_single to return None (failed fetch)
    with patch('app.services.favorites_service.sync_xiaohongshu_note_details_single',
               new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = None

        # Create syncer with retry settings
        from app.services.xiaohongshu_event_handler import DefaultXiaohongshuDetailsSyncer
        syncer = DefaultXiaohongshuDetailsSyncer(retry_delay_minutes=0, max_attempts=3)

        # First attempt should call sync
        result = await syncer.sync_details(db_session, [item])
        assert len(result) == 0  # No items with details
        assert mock_sync.called

        # Refresh item to see updated attempts
        await db_session.refresh(item)
        assert item.details_fetch_attempts == 1


@pytest.mark.asyncio
async def test_xiaohongshu_task_creation_only_with_details(db_session):
    """Test that tasks are only created when details are successfully fetched."""
    # Setup: Create workshop
    workshop = WorkshopModel(
        workshop_id="test_workshop",
        name="Test Workshop",
        default_prompt="Test prompt",
        executor_type="llm_chat",
        executor_config=json.dumps({
            "listening_enabled": True,
            "platform_bindings": [
                {"platform": "xiaohongshu", "collection_ids": [1]}
            ]
        })
    )
    db_session.add(workshop)

    # Create author
    author = Author(
        platform_user_id="user_task_test",
        platform=PlatformEnum.xiaohongshu,
        username="测试用户",
        avatar_url="avatar.jpg"
    )
    db_session.add(author)
    await db_session.commit()
    await db_session.refresh(author)

    # Create collection
    collection = Collection(
        platform_collection_id="col_task_test",
        platform=PlatformEnum.xiaohongshu,
        title="Test Collection",
        author_id=author.id
    )
    db_session.add(collection)
    await db_session.commit()
    await db_session.refresh(collection)

    # Create item WITHOUT details (desc is empty)
    item_no_details = FavoriteItem(
        platform_item_id="note_no_details",
        platform=PlatformEnum.xiaohongshu,
        item_type=ItemTypeEnum.note,
        title="Note Without Details",
        intro="",
        cover_url="cover.jpg",
        favorited_at=datetime.utcnow(),
        author_id=author.id,
        collection_id="col_task_test"
    )
    db_session.add(item_no_details)

    # Add minimal detail record
    detail_no_data = XiaohongshuNoteDetail(
        favorite_item_id=item_no_details.id,
        note_id="note_no_details",
        xsec_token="token",
        desc="",  # Empty = no details
        ip_location="",
        published_date=""
    )
    db_session.add(detail_no_data)

    # Create item WITH details
    item_with_details = FavoriteItem(
        platform_item_id="note_with_details",
        platform=PlatformEnum.xiaohongshu,
        item_type=ItemTypeEnum.note,
        title="Note With Details",
        intro="Full description",
        cover_url="cover.jpg",
        favorited_at=datetime.utcnow(),
        author_id=author.id,
        collection_id="col_task_test"
    )
    db_session.add(item_with_details)

    # Add full detail record
    detail_with_data = XiaohongshuNoteDetail(
        favorite_item_id=item_with_details.id,
        note_id="note_with_details",
        xsec_token="token",
        desc="This is a complete description",  # Has content
        ip_location="上海",
        published_date="2024-01-01",
        like_count=100,
        collect_count=50
    )
    db_session.add(detail_with_data)

    await db_session.commit()
    await db_session.refresh(item_no_details)
    await db_session.refresh(item_with_details)

    # Test task creator
    from app.services.xiaohongshu_event_handler import DefaultXiaohongshuTaskCreator
    task_creator = DefaultXiaohongshuTaskCreator()

    # Mock workshop_service to avoid actual task execution
    with patch('app.services.workshop_service.start_workshop_task', new_callable=AsyncMock) as mock_start:
        mock_start.return_value = AsyncMock(id=1)

        with patch('app.services.workshop_service.run_workshop_task', new_callable=AsyncMock):
            # Try to create tasks for both items
            await task_creator.create_analysis_tasks(
                db_session,
                [item_no_details, item_with_details],
                {}
            )

    # Verify: start_workshop_task should only be called once (for item WITH details)
    assert mock_start.call_count == 1


@pytest.mark.asyncio
async def test_xiaohongshu_event_routing(sample_xiaohongshu_event):
    """Test that Xiaohongshu events are correctly routed to the Xiaohongshu handler."""
    from app.services.listener_service import handle_stream_event

    # Mock the orchestrator to verify it's called
    with patch('app.services.xiaohongshu_event_handler.create_xiaohongshu_event_orchestrator') as mock_create:
        mock_orchestrator = AsyncMock()
        mock_create.return_value = mock_orchestrator

        # Handle event
        await handle_stream_event(sample_xiaohongshu_event)

        # Verify Xiaohongshu orchestrator was created
        mock_create.assert_called_once()

        # Verify event was handled
        mock_orchestrator.handle_event.assert_called_once()
