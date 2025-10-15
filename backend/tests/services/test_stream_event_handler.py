"""
Unit tests for Stream Event Handler module.

Tests each component in isolation using mocks and fixtures.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.stream_event_handler import (
    CreatorInfo,
    VideoItemBrief,
    StreamEventData,
    BilibiliEventParser,
    BilibiliItemPersister,
    BilibiliDetailsSyncer,
    WorkshopTaskCreator,
    StreamEventOrchestrator
)


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_creator_dict():
    """Sample creator data from event."""
    return {
        "user_id": "12345",
        "username": "TestUser",
        "avatar": "http://example.com/avatar.jpg"
    }


@pytest.fixture
def sample_video_dict(sample_creator_dict):
    """Sample video item data from event."""
    return {
        "bvid": "BV1234567890",
        "collection_id": "3706749228",
        "title": "Test Video",
        "intro": "Test description",
        "cover": "http://example.com/cover.jpg",
        "fav_time": 1757488420,
        "creator": sample_creator_dict
    }


@pytest.fixture
def sample_event(sample_video_dict):
    """Sample complete event structure."""
    return {
        "event_id": "test-event-123",
        "payload": {
            "result": {
                "success": True,
                "data": {
                    "added": {
                        "count": 1,
                        "data": [sample_video_dict]
                    },
                    "data": [sample_video_dict]
                }
            }
        }
    }


# ============================================================================
# DTO Tests
# ============================================================================

class TestCreatorInfo:
    """Test CreatorInfo DTO."""
    
    def test_from_dict_valid(self, sample_creator_dict):
        """Test creating CreatorInfo from valid dict."""
        creator = CreatorInfo.from_dict(sample_creator_dict)
        assert creator.user_id == "12345"
        assert creator.username == "TestUser"
        assert creator.avatar == "http://example.com/avatar.jpg"
    
    def test_from_dict_missing_fields(self):
        """Test creating CreatorInfo with missing fields."""
        creator = CreatorInfo.from_dict({})
        assert creator.user_id == ""
        assert creator.username == ""
        assert creator.avatar == ""


class TestVideoItemBrief:
    """Test VideoItemBrief DTO."""
    
    def test_from_dict_valid(self, sample_video_dict):
        """Test creating VideoItemBrief from valid dict."""
        item = VideoItemBrief.from_dict(sample_video_dict)
        assert item is not None
        assert item.bvid == "BV1234567890"
        assert item.collection_id == "3706749228"
        assert item.title == "Test Video"
        assert item.fav_time == 1757488420
        assert isinstance(item.creator, CreatorInfo)
    
    def test_from_dict_missing_bvid(self, sample_video_dict):
        """Test that missing bvid returns None."""
        sample_video_dict.pop("bvid")
        item = VideoItemBrief.from_dict(sample_video_dict)
        assert item is None


# ============================================================================
# Parser Tests
# ============================================================================

class TestBilibiliEventParser:
    """Test BilibiliEventParser."""
    
    def test_parse_valid_event(self, sample_event):
        """Test parsing valid event."""
        parser = BilibiliEventParser()
        result = parser.parse(sample_event)
        
        assert isinstance(result, StreamEventData)
        assert len(result.items) == 1
        assert result.items[0].bvid == "BV1234567890"
        assert result.has_items is True
    
    def test_parse_empty_event(self):
        """Test parsing empty event."""
        parser = BilibiliEventParser()
        result = parser.parse({})
        
        assert isinstance(result, StreamEventData)
        assert len(result.items) == 0
        assert result.has_items is False
    
    def test_parse_failed_event(self):
        """Test parsing event with success=false."""
        event = {
            "payload": {
                "result": {
                    "success": False,
                    "error": "Some error"
                }
            }
        }
        parser = BilibiliEventParser()
        result = parser.parse(event)
        
        assert len(result.items) == 0


# ============================================================================
# Persister Tests
# ============================================================================

@pytest.mark.asyncio
class TestBilibiliItemPersister:
    """Test BilibiliItemPersister."""
    
    async def test_persist_new_item(self, sample_video_dict):
        """Test persisting a new item."""
        # Setup mocks
        mock_crud = MagicMock()
        mock_crud.favorite_item.get_by_platform_item_id = AsyncMock(return_value=None)
        mock_crud.author.get_by_platform_id = AsyncMock(return_value=None)
        mock_crud.author.create = AsyncMock(return_value=MagicMock(id=1))
        mock_crud.collection.get_by_platform_id = AsyncMock(return_value=MagicMock(id=2))
        mock_crud.favorite_item.create_brief_with_relationships = AsyncMock(
            return_value=MagicMock(id=100, platform_item_id="BV1234567890")
        )
        
        persister = BilibiliItemPersister(mock_crud)
        item = VideoItemBrief.from_dict(sample_video_dict)
        
        # Execute
        db = MagicMock()
        result = await persister.persist_brief_items(db, [item])
        
        # Assert
        assert len(result) == 1
        assert result[0].id == 100
        mock_crud.favorite_item.create_brief_with_relationships.assert_called_once()
    
    async def test_persist_existing_item(self, sample_video_dict):
        """Test that existing items are returned without creation."""
        # Setup mocks
        existing_item = MagicMock(id=50, platform_item_id="BV1234567890")
        mock_crud = MagicMock()
        mock_crud.favorite_item.get_by_platform_item_id = AsyncMock(return_value=existing_item)
        
        persister = BilibiliItemPersister(mock_crud)
        item = VideoItemBrief.from_dict(sample_video_dict)
        
        # Execute
        db = MagicMock()
        result = await persister.persist_brief_items(db, [item])
        
        # Assert
        assert len(result) == 1
        assert result[0].id == 50
        mock_crud.favorite_item.create_brief_with_relationships.assert_not_called()


# ============================================================================
# Syncer Tests
# ============================================================================

@pytest.mark.asyncio
class TestBilibiliDetailsSyncer:
    """Test BilibiliDetailsSyncer."""
    
    async def test_sync_details_with_items(self):
        """Test syncing details for items."""
        mock_service = MagicMock()
        mock_service.sync_bilibili_videos_details = AsyncMock()
        
        syncer = BilibiliDetailsSyncer(mock_service)
        
        items = [
            MagicMock(platform_item_id="BV111"),
            MagicMock(platform_item_id="BV222")
        ]
        
        db = MagicMock()
        await syncer.sync_details(db, items)
        
        mock_service.sync_bilibili_videos_details.assert_called_once_with(
            db, bvids=["BV111", "BV222"]
        )
    
    async def test_sync_details_no_items(self):
        """Test syncing with no items."""
        mock_service = MagicMock()
        mock_service.sync_bilibili_videos_details = AsyncMock()
        
        syncer = BilibiliDetailsSyncer(mock_service)
        
        db = MagicMock()
        await syncer.sync_details(db, [])
        
        mock_service.sync_bilibili_videos_details.assert_not_called()


# ============================================================================
# Task Creator Tests
# ============================================================================

@pytest.mark.asyncio
class TestWorkshopTaskCreator:
    """Test WorkshopTaskCreator."""
    
    async def test_create_task_with_details(self):
        """Test creating task for item with details."""
        # Setup mocks
        mock_crud = MagicMock()
        full_item = MagicMock(bilibili_video_details=MagicMock())
        mock_crud.favorite_item.get_by_platform_item_id_with_details = AsyncMock(
            return_value=full_item
        )
        
        mock_workshop = MagicMock()
        mock_workshop.start_workshop_task = AsyncMock(return_value=MagicMock(id=1))
        mock_workshop.run_workshop_task = AsyncMock()
        
        creator = WorkshopTaskCreator(mock_crud, mock_workshop)
        
        # Mock database queries
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        ))
        
        # Execute
        item = MagicMock(id=10, platform_item_id="BV123")
        with patch('app.services.listener_service._resolve_workshop_id_for_item', 
                   new=AsyncMock(return_value="workshop-1")):
            await creator.create_analysis_tasks(db, [item], {})
        
        # Assert
        mock_workshop.start_workshop_task.assert_called_once()
    
    async def test_skip_task_without_details(self):
        """Test that items without details are skipped."""
        # Setup mocks
        mock_crud = MagicMock()
        mock_crud.favorite_item.get_by_platform_item_id_with_details = AsyncMock(
            return_value=MagicMock(bilibili_video_details=None)
        )
        
        mock_workshop = MagicMock()
        mock_workshop.start_workshop_task = AsyncMock()
        
        creator = WorkshopTaskCreator(mock_crud, mock_workshop)
        
        # Execute
        db = MagicMock()
        item = MagicMock(id=10, platform_item_id="BV123")
        await creator.create_analysis_tasks(db, [item], {})
        
        # Assert
        mock_workshop.start_workshop_task.assert_not_called()


# ============================================================================
# Orchestrator Tests
# ============================================================================

@pytest.mark.asyncio
class TestStreamEventOrchestrator:
    """Test StreamEventOrchestrator."""
    
    async def test_full_pipeline(self, sample_event):
        """Test the complete event processing pipeline."""
        # Setup mocks
        mock_parser = MagicMock()
        mock_parser.parse = MagicMock(return_value=StreamEventData(
            items=[VideoItemBrief.from_dict(sample_event["payload"]["result"]["data"]["data"][0])],
            event_metadata=sample_event
        ))
        
        mock_persister = MagicMock()
        mock_persister.persist_brief_items = AsyncMock(
            return_value=[MagicMock(id=1, platform_item_id="BV123")]
        )
        
        mock_syncer = MagicMock()
        mock_syncer.sync_details = AsyncMock()
        
        mock_task_creator = MagicMock()
        mock_task_creator.create_analysis_tasks = AsyncMock()
        
        orchestrator = StreamEventOrchestrator(
            parser=mock_parser,
            persister=mock_persister,
            syncer=mock_syncer,
            task_creator=mock_task_creator
        )
        
        # Execute
        db = MagicMock()
        await orchestrator.handle_event(sample_event, db)
        
        # Assert all steps were called
        mock_parser.parse.assert_called_once_with(sample_event)
        mock_persister.persist_brief_items.assert_called_once()
        mock_syncer.sync_details.assert_called_once()
        mock_task_creator.create_analysis_tasks.assert_called_once()
    
    async def test_pipeline_with_no_items(self):
        """Test pipeline stops early when no items."""
        # Setup mocks
        mock_parser = MagicMock()
        mock_parser.parse = MagicMock(return_value=StreamEventData(
            items=[],
            event_metadata={}
        ))
        
        mock_persister = MagicMock()
        mock_persister.persist_brief_items = AsyncMock()
        
        orchestrator = StreamEventOrchestrator(
            parser=mock_parser,
            persister=mock_persister,
            syncer=MagicMock(),
            task_creator=MagicMock()
        )
        
        # Execute
        db = MagicMock()
        await orchestrator.handle_event({}, db)
        
        # Assert persistence was not called
        mock_persister.persist_brief_items.assert_not_called()
