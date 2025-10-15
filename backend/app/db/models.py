import datetime
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Table, Text, Enum, Float)
from sqlalchemy.orm import relationship, Mapped
from .base import Base
import enum

class PlatformEnum(str, enum.Enum):
    bilibili = "bilibili"
    xiaohongshu = "xiaohongshu"

class ItemTypeEnum(str, enum.Enum):
    video = "video"
    note = "note"

class FavoriteItemStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"

item_tags = Table(
    "item_tags",
    Base.metadata,
    Column("item_id", Integer, ForeignKey("favorite_items.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    platform_user_id = Column(String, nullable=False, index=True)
    platform = Column(Enum(PlatformEnum), nullable=False)
    username = Column(String, nullable=False)
    avatar_url = Column(String)
    
    items = relationship("FavoriteItem", back_populates="author", lazy="selectin")
    collections = relationship("Collection", back_populates="author", lazy="selectin")


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    platform_collection_id = Column(String, nullable=False, index=True)
    platform = Column(Enum(PlatformEnum), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    cover_url = Column(String)
    item_count = Column(Integer, default=0)
    
    author_id = Column(Integer, ForeignKey("authors.id"))
    author = relationship("Author", back_populates="collections", lazy="selectin")
    
    items = relationship("FavoriteItem", back_populates="collection", lazy="selectin")


class FavoriteItem(Base):
    __tablename__ = "favorite_items"

    id = Column(Integer, primary_key=True, index=True)
    platform_item_id = Column(String, nullable=False, index=True, unique=True)
    # Optional: platform-level favorite ID (e.g., Bilibili favorite record id)
    platform_favorite_id = Column(String)
    platform = Column(Enum(PlatformEnum), nullable=False)
    item_type = Column(Enum(ItemTypeEnum), nullable=False)
    title = Column(String, nullable=False)
    intro = Column(Text)
    cover_url = Column(String)
    status = Column(Enum(FavoriteItemStatus), nullable=False, default=FavoriteItemStatus.PENDING, index=True)

    published_at = Column(DateTime)
    favorited_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Details fetch retry mechanism (for Xiaohongshu primarily)
    details_fetch_attempts = Column(Integer, default=0)
    details_last_attempt_at = Column(DateTime)
    details_fetch_error = Column(Text)  # Last error message

    author_id = Column(Integer, ForeignKey("authors.id"))
    author = relationship("Author", back_populates="items", lazy="selectin")
    
    collection = relationship("Collection", back_populates="items", lazy="selectin")
    collection_id = Column(String, ForeignKey("collections.platform_collection_id"))

    tags = relationship("Tag", secondary=item_tags, back_populates="items", lazy="selectin")

    bilibili_video_details = relationship("BilibiliVideoDetail", back_populates="favorite_item", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    xiaohongshu_note_details = relationship("XiaohongshuNoteDetail", back_populates="favorite_item", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    results = relationship("Result", back_populates="favorite_item", cascade="all, delete-orphan", lazy="selectin")
    tasks = relationship("Task", back_populates="favorite_item", cascade="all, delete-orphan", lazy="selectin")
    # subtitles are related to the video details, not the favorite item itself. Moving this relationship.

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    items = relationship("FavoriteItem", secondary=item_tags, back_populates="tags", lazy="selectin")


class BilibiliVideoDetail(Base):
    __tablename__ = "bilibili_video_details"
    
    id = Column(Integer, primary_key=True, index=True)
    bvid = Column(String, unique=True, index=True)
    
    # Details from BiliVideoDetails dataclass
    tname = Column(String)
    tname_v2 = Column(String)
    
    # Details from VideoDimension dataclass
    dimension_width = Column(Integer)
    dimension_height = Column(Integer)
    dimension_rotate = Column(Integer)
    
    # Details from VideoStatistic dataclass
    duration_sec = Column(Integer)
    view_count = Column(Integer)
    like_count = Column(Integer)
    coin_count = Column(Integer)
    favorite_count = Column(Integer)
    reply_count = Column(Integer)
    share_count = Column(Integer)
    danmaku_count = Column(Integer)
    
    favorite_item_id = Column(Integer, ForeignKey("favorite_items.id"), nullable=False)
    favorite_item = relationship("FavoriteItem", back_populates="bilibili_video_details", lazy="selectin")

    # Relationships to media URLs and subtitles
    video_url = relationship("BilibiliVideoUrl", back_populates="video_detail", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    audio_url = relationship("BilibiliAudioUrl", back_populates="video_detail", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    subtitles = relationship("BilibiliSubtitle", back_populates="video_detail", cascade="all, delete-orphan", lazy="selectin")

# New table for Video URLs
class BilibiliVideoUrl(Base):
    __tablename__ = "bilibili_video_urls"
    id = Column(Integer, primary_key=True, index=True)
    platform_media_id = Column(String)
    base_url = Column(Text)
    backup_url = Column(Text)
    bandwidth = Column(Integer)
    mime_type = Column(String)
    codecs = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    frame_rate = Column(String)
    
    video_detail_id = Column(Integer, ForeignKey("bilibili_video_details.id"), nullable=False, unique=True)
    video_detail = relationship("BilibiliVideoDetail", back_populates="video_url", lazy="selectin")

# New table for Audio URLs
class BilibiliAudioUrl(Base):
    __tablename__ = "bilibili_audio_urls"
    id = Column(Integer, primary_key=True, index=True)
    platform_media_id = Column(String)
    base_url = Column(Text)
    backup_url = Column(Text)
    bandwidth = Column(Integer)
    mime_type = Column(String)
    codecs = Column(String)

    video_detail_id = Column(Integer, ForeignKey("bilibili_video_details.id"), nullable=False, unique=True)
    video_detail = relationship("BilibiliVideoDetail", back_populates="audio_url", lazy="selectin")

# New table for Subtitles
class BilibiliSubtitle(Base):
    __tablename__ = "bilibili_subtitles"
    id = Column(Integer, primary_key=True, index=True)
    sid = Column(Integer)
    lang = Column(String)
    content = Column(Text)
    from_sec = Column(Float)
    to_sec = Column(Float)
    
    video_detail_id = Column(Integer, ForeignKey("bilibili_video_details.id"), nullable=False)
    video_detail = relationship("BilibiliVideoDetail", back_populates="subtitles", lazy="selectin")

# Xiaohongshu Note Details
class XiaohongshuNoteDetail(Base):
    __tablename__ = "xiaohongshu_note_details"

    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(String, unique=True, index=True, nullable=False)
    xsec_token = Column(String)

    # Description field
    desc = Column(Text)

    # Location information
    ip_location = Column(String)  # ip_zh in source

    # Publication date
    published_date = Column(String)  # date field from source

    # Statistics
    like_count = Column(Integer)
    collect_count = Column(Integer)
    comment_count = Column(Integer)
    share_count = Column(Integer)

    # Timestamp when data was fetched
    fetched_timestamp = Column(String)

    favorite_item_id = Column(Integer, ForeignKey("favorite_items.id"), nullable=False)
    favorite_item = relationship("FavoriteItem", back_populates="xiaohongshu_note_details", lazy="selectin")

    # Relationships to images and video
    images = relationship("XiaohongshuNoteImage", back_populates="note_detail", cascade="all, delete-orphan", lazy="selectin")
    video = relationship("XiaohongshuNoteVideo", back_populates="note_detail", uselist=False, cascade="all, delete-orphan", lazy="selectin")


# Xiaohongshu Note Images
class XiaohongshuNoteImage(Base):
    __tablename__ = "xiaohongshu_note_images"

    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(Text, nullable=False)
    order_index = Column(Integer, default=0)  # To maintain order

    note_detail_id = Column(Integer, ForeignKey("xiaohongshu_note_details.id"), nullable=False)
    note_detail = relationship("XiaohongshuNoteDetail", back_populates="images", lazy="selectin")


# Xiaohongshu Note Video
class XiaohongshuNoteVideo(Base):
    __tablename__ = "xiaohongshu_note_videos"

    id = Column(Integer, primary_key=True, index=True)

    # Video information (structure from VideoInfo dataclass)
    video_url = Column(Text)
    duration = Column(Integer)  # Duration in seconds or milliseconds
    width = Column(Integer)
    height = Column(Integer)
    thumbnail_url = Column(String)

    note_detail_id = Column(Integer, ForeignKey("xiaohongshu_note_details.id"), nullable=False, unique=True)
    note_detail = relationship("XiaohongshuNoteDetail", back_populates="video", lazy="selectin")

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(String, nullable=False, index=True)
    content = Column(Text) # Or JSON if the output is structured
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    favorite_item_id = Column(Integer, ForeignKey("favorite_items.id"), nullable=False)
    favorite_item = relationship("FavoriteItem", back_populates="results", lazy="selectin")
    
    task_id = Column(Integer, ForeignKey("tasks.id"))
    task = relationship("Task", back_populates="result", lazy="selectin")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING, index=True)
    workshop_id = Column(String)
    # Optional: allow custom prompt and model per task
    prompt = Column(Text)
    llm_model = Column(String)
    
    favorite_item_id = Column(Integer, ForeignKey("favorite_items.id"))
    favorite_item = relationship("FavoriteItem", back_populates="tasks", lazy="selectin")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    result = relationship("Result", back_populates="task", uselist=False, cascade="all, delete-orphan", lazy="selectin")


class AppSetting(Base):
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)


class Workshop(Base):
    __tablename__ = "workshops"
    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    default_prompt = Column(Text, nullable=False)
    default_model = Column(String)
    executor_type = Column(String, nullable=False, default="llm_chat")
    executor_config = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class NotificationStatus(str, enum.Enum):
    """Status of notification delivery."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class NotificationLog(Base):
    """
    Log of notification delivery attempts.

    Records every notification sent through the system, including
    success/failure status, content snapshots, and external IDs.
    """
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Source reference
    result_id = Column(Integer, ForeignKey("results.id"), nullable=False, index=True)
    result = relationship("Result", lazy="selectin")

    # Pipeline identification
    pipeline_name = Column(String, nullable=False, index=True)
    notifier_type = Column(String, nullable=False, index=True)

    # Delivery status
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING, index=True)

    # Content snapshot (for debugging/auditing)
    content_snapshot = Column(Text)  # Truncated version of sent content

    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # External platform reference
    external_id = Column(String)  # e.g., Xiaohongshu note ID, email message ID

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    sent_at = Column(DateTime)  # When successfully delivered

    # Metadata (JSON string)
    # metadata = Column(Text)  # JSON-serialized dict for flexible data storage
