import asyncio
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging_config import get_logger
from app.db.models import FavoriteItem, Workshop as WorkshopModel
from client_sdk.params import TaskParams
from client_sdk.rpc_client_async import EAIRPCClient
from app.core.config import settings

logger = get_logger(__name__)

class ExecutionContext:
    def __init__(self, db: AsyncSession, task_id: int, favorite_item_id: int) -> None:
        self.db = db
        self.task_id = task_id
        self.favorite_item_id = favorite_item_id


class SourceTextBuilder:
    """Elegant builder for constructing rich source text from favorite items."""
    
    def __init__(self, item):
        self.item = item
        self.sections = []
    
    def add_basic_info(self):
        """Add title and intro."""
        if self.item.title:
            self.sections.append(f"标题: {self.item.title}")
        if self.item.intro:
            self.sections.append(f"简介: {self.item.intro}")
        return self
    
    def add_author_info(self):
        """Add author metadata."""
        if self.item.author:
            self.sections.append(f"作者: {self.item.author.username}")
        return self
    
    def add_tags(self):
        """Add content tags."""
        if self.item.tags:
            tag_names = ", ".join(tag.name for tag in self.item.tags)
            self.sections.append(f"标签: {tag_names}")
        return self
    
    def add_video_metadata(self):
        """Add video classification and statistics."""
        if not self.item.bilibili_video_details:
            return self
        
        details = self.item.bilibili_video_details
        
        if details.tname:
            self.sections.append(f"分类: {details.tname}")
        
        stats = [
            f"播放{details.view_count}" if details.view_count else None,
            f"点赞{details.like_count}" if details.like_count else None,
            f"投币{details.coin_count}" if details.coin_count else None,
        ]
        stats = [s for s in stats if s]
        if stats:
            self.sections.append(f"数据: {' · '.join(stats)}")
        
        return self
    
    def add_subtitles(self, max_lines: int = 100):
        """Add video subtitles (critical for content understanding)."""
        try:
            if not self.item.bilibili_video_details:
                return self

            details = self.item.bilibili_video_details
            if not details.subtitles:
                return self

            # Safely access subtitles (already loaded via selectinload)
            subtitles = list(details.subtitles)[:max_lines]
            if not subtitles:
                return self

            subtitle_text = "\n".join(sub.content for sub in subtitles)

            if subtitle_text:
                self.sections.append(f"\n字幕内容:\n{subtitle_text}")
        except Exception as e:
            logger.warning(f"Failed to add subtitles: {e}")

        return self

    def add_xiaohongshu_metadata(self):
        """Add Xiaohongshu note metadata and statistics."""
        if not self.item.xiaohongshu_note_details:
            return self

        details = self.item.xiaohongshu_note_details

        # Add location if available
        if details.ip_location:
            self.sections.append(f"发布地点: {details.ip_location}")

        # Add published date
        if details.published_date:
            self.sections.append(f"发布时间: {details.published_date}")

        # Add statistics
        stats = [
            f"点赞{details.like_count}" if details.like_count else None,
            f"收藏{details.collect_count}" if details.collect_count else None,
            f"评论{details.comment_count}" if details.comment_count else None,
        ]
        stats = [s for s in stats if s]
        if stats:
            self.sections.append(f"数据: {' · '.join(stats)}")

        return self

    def add_xiaohongshu_images(self, max_images: int = 9):
        """Add Xiaohongshu note images (for reference)."""
        try:
            if not self.item.xiaohongshu_note_details:
                return self

            details = self.item.xiaohongshu_note_details
            if not details.images:
                return self

            # Take first N images
            images = list(details.images)[:max_images]
            if not images:
                return self

            image_urls = [img.image_url for img in images]
            self.sections.append(f"\n包含 {len(image_urls)} 张图片")

        except Exception as e:
            logger.warning(f"Failed to add images: {e}")

        return self

    def add_xiaohongshu_video(self):
        """Add Xiaohongshu video info if available."""
        try:
            if not self.item.xiaohongshu_note_details:
                return self

            details = self.item.xiaohongshu_note_details
            if not details.video:
                return self

            video = details.video
            if video.duration:
                duration_sec = video.duration // 1000 if video.duration > 1000 else video.duration
                self.sections.append(f"视频时长: {duration_sec}秒")

        except Exception as e:
            logger.warning(f"Failed to add video info: {e}")

        return self
    
    def build(self) -> str:
        """Construct final source text."""
        return "\n".join(self.sections)


async def _ensure_details_synced(db: AsyncSession, item) -> None:
    """
    Check for missing video details.
    
    NOTE: Auto-sync is DISABLED to prevent blocking task execution.
    Users should manually sync details before running workshops for best results.
    """
    if item.platform != "bilibili":
        return
    
    # Just log a warning if details are missing - don't auto-sync
    if not item.bilibili_video_details:
        logger.warning(
            f"⚠️ Item {item.platform_item_id} lacks detailed info (subtitles, stats). "
            f"For better AI results, sync details first: "
            f"POST /api/v1/sync/bilibili/videos/details {{\"bvids\": [\"{item.platform_item_id}\"]}}"
        )


async def _build_source_text(db: AsyncSession, favorite_item_id: int) -> str:
    """Build comprehensive source text with optional auto-sync."""
    from app.crud import crud_favorites

    item = await crud_favorites.favorite_item.get_full(db, id=favorite_item_id)
    if not item:
        return ""

    # Check if details are missing and warn (but don't auto-sync to avoid blocking)
    if item.platform == "bilibili" and not item.bilibili_video_details:
        logger.warning(
            f"Item {item.platform_item_id} is missing detailed info (subtitles, etc.). "
            f"AI result quality may be reduced. Please sync details first via "
            f"POST /api/v1/sync/bilibili/videos/details with bvids=['{item.platform_item_id}']"
        )
    elif item.platform == "xiaohongshu" and not item.xiaohongshu_note_details:
        logger.warning(
            f"Item {item.platform_item_id} is missing detailed info (images, desc, etc.). "
            f"AI result quality may be reduced. Please sync details first via "
            f"POST /api/v1/sync/xiaohongshu/notes/details with note_ids=['{item.platform_item_id}']"
        )

    # Build rich text using elegant builder pattern (use whatever data is available)
    builder = (
        SourceTextBuilder(item)
        .add_basic_info()
        .add_author_info()
        .add_tags()
    )

    # Platform-specific enrichment
    if item.platform == "bilibili":
        builder.add_video_metadata().add_subtitles()
    elif item.platform == "xiaohongshu":
        builder.add_xiaohongshu_metadata().add_xiaohongshu_images().add_xiaohongshu_video()

    return builder.build()


async def execute_llm_chat(ctx: ExecutionContext, *, prompt_template: str, model: Optional[str]) -> str:
    prompt_template = prompt_template
    source = await _build_source_text(ctx.db, ctx.favorite_item_id)
    prompt = prompt_template.replace("{source}", source)
    prompt = prompt.replace('\n', '').replace('\r', '')

    client = EAIRPCClient(base_url=settings.EAI_BASE_URL, api_key=settings.EAI_API_KEY)
    try:
        await client.start()
        result = await client.chat_with_yuanbao(
            ask_question=prompt,
            conversation_id=settings.YUANBAO_CONVERSATION_ID,
            task_params=TaskParams(
                cookie_ids=settings.YUANBAO_COOKIE_IDS,
                close_page_when_task_finished=True,
            )
        )
        response_text = result.get('data')[0].get('last_model_message', 'N/A')
        return response_text
    except Exception as e:
        logger.error(f"LLM execution failed: {e}", exc_info=True)
        raise  # Re-raise to let workshop_service handle it
    finally:
        await client.stop()


Executor = Any


class ExecutorRegistry:
    def __init__(self) -> None:
        self._executors: Dict[str, Executor] = {
            "llm_chat": execute_llm_chat,
        }

    def get(self, executor_type: str) -> Executor:
        return self._executors.get(executor_type, execute_llm_chat)


executor_registry = ExecutorRegistry()


