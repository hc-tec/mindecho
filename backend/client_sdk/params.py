from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Tuple, Sequence


# Copy from src/core/task_params.py
@dataclass
class TaskParams:
    """Task configuration container with extensibility.

    Common options are exposed as typed attributes, while any additional
    plugin-specific options are stored in ``extra``. The object behaves like
    a read-only mapping that merges common fields and ``extra``.
    """

    # Common, strongly-typed fields
    headless: Optional[bool] = None
    cookie_ids: List[str] = field(default_factory=list)
    viewport: Optional[Dict[str, int]] = None
    user_agent: Optional[str] = None
    extra_http_headers: Optional[Dict[str, str]] = None
    close_page_when_task_finished: bool = False

    # Don't need [extra] field in client_sdk

# Copy from src/services/base_service.py
@dataclass
class ServiceParams:
    """Common configuration for services.

    Attributes:
        response_timeout_sec: Max seconds to wait for a response event.
        delay_ms: Delay between pages/batches/polls (when applicable).
        queue_maxsize: Optional queue size hint for internal buffers.
        max_pages: Optional page limit for paginated collectors.
        scroll_pause_ms: Pause after each scroll, in milliseconds.
        max_idle_rounds: Stop after this many consecutive idle rounds (for DOM collectors or custom loops).
        max_items: Optional item limit (applies where relevant).
        scroll_mode: Optional strategy indicator: "default" | "selector" | "pager".
        scroll_selector: Used when scroll_mode == "selector".
        pager_selector: Used when scroll_mode == "pager".
    """

    response_timeout_sec: float = 3.0
    delay_ms: int = 500
    queue_maxsize: Optional[int] = None
    scroll_pause_ms: int = 800
    max_idle_rounds: int = 1
    max_items: Optional[int] = 10000
    max_seconds: int = 600
    auto_scroll: bool = True
    scroll_mode: Optional[str] = None
    scroll_selector: Optional[str] = None
    max_pages: Optional[int] = None
    pager_selector: Optional[str] = None
    need_raw_data: bool = False


@dataclass
class SyncParams:
    """用于被动数据同步和停止条件的配置。

    属性：
        identity_key: 用于唯一标识记录的字段名。
        deletion_policy: 'soft' 表示标记删除，'hard' 表示物理删除文档。
        soft_delete_flag: 用于标记软删除文档的字段名。
        soft_delete_time_key: 用于存储软删除时间戳的字段名。
        stop_after_consecutive_known: 当一个批次包含如此多连续的已知项时停止同步。假设设置 stop_after_consecutive_known = 5，
            那么当连续 5 条数据都是已经同步过的记录（没有发生任何变化）时，系统会停止进一步的同步，因为认为数据已经同步完成，不再需要继续抓取。
        stop_after_no_change_batches: 在没有新增或更新的批次后停止同步的批次数量。也就是说，数据抓取了一段时间后，
            如果连续几个批次都没有发现任何变化，可能说明数据已经同步完毕，或者数据源没有更多更新，于是自动停止抓取。
        max_new_items: 当本次会话中收集到的新项达到此限制时停止同步。

    Configuration for passive data synchronization and stop conditions.

    Attributes:
        identity_key: Field name used to uniquely identify a record.
        deletion_policy: 'soft' to mark deletions, 'hard' to remove documents.
        soft_delete_flag: Field name used to mark soft-deleted documents.
        soft_delete_time_key: Field name used to store deletion timestamp on soft delete.
        stop_after_consecutive_known: Stop when a batch contains this many consecutive already-known items.
        stop_after_no_change_batches: Stop after this many batches without additions or updates.
        max_new_items: Stop when new items collected in this session reach this limit.
    """

    identity_key: str = "id"
    deletion_policy: str = "soft"
    soft_delete_flag: str = "deleted"
    soft_delete_time_key: str = "deleted_at"
    stop_after_consecutive_known: Optional[int] = None
    stop_after_no_change_batches: Optional[int] = None
    max_new_items: Optional[int] = None
    # Fingerprint-based update detection (for sources without reliable updated_at)
    fingerprint_fields: Optional[Sequence[str]] = None  # None -> use all fields except bookkeeping keys
    fingerprint_key: str = "_fingerprint"
    fingerprint_algorithm: str = "sha1"  # sha1|sha256
