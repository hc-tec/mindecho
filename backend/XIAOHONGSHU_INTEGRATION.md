# 小红书集成完成文档

## 概述

已成功将小红书（Xiaohongshu）数据支持添加到 MindEcho 系统中，与现有的 B站集成保持一致的架构和最佳实践。

## 实现的功能

### 1. 数据库模型（`backend/app/db/models.py`）

添加了以下模型：

- **XiaohongshuNoteDetail**: 小红书笔记详情主表
  - `note_id`: 笔记ID（唯一索引）
  - `xsec_token`: 安全令牌
  - `desc`: 笔记描述
  - `ip_location`: 发布地点
  - `published_date`: 发布日期
  - 统计数据：`like_count`, `collect_count`, `comment_count`, `share_count`
  - `fetched_timestamp`: 数据抓取时间戳

- **XiaohongshuNoteImage**: 笔记图片表（一对多关系）
  - `image_url`: 图片URL
  - `order_index`: 图片顺序

- **XiaohongshuNoteVideo**: 笔记视频表（一对一关系）
  - `video_url`: 视频URL
  - `duration`: 时长
  - `width`, `height`: 尺寸
  - `thumbnail_url`: 缩略图

- **FavoriteItem**: 更新以支持小红书
  - 添加关系：`xiaohongshu_note_details`

### 2. Pydantic Schemas（`backend/app/schemas/unified.py`）

添加了完整的请求/响应模式：

- `XiaohongshuNoteImageBase/Create/Schema`
- `XiaohongshuNoteVideoBase/Create/Schema`
- `XiaohongshuNoteDetailBase/Create/Schema`
- 更新 `FavoriteItem` schema 以包含小红书详情

### 3. CRUD 操作（`backend/app/crud/crud_favorites.py`）

更新了 `CRUDFavoriteItem._apply_full_load_options()` 方法：
- 添加 `xiaohongshu_note_details` 的预加载
- 包括嵌套的 `images` 和 `video` 关系

### 4. 同步服务（`backend/app/services/favorites_service.py`）

添加了完整的同步函数集：

#### 数据结构
```python
@dataclass
class NoteStatistics:
    like_count, collect_count, comment_count, share_count

@dataclass
class VideoInfo:
    video_url, duration, width, height, thumbnail_url

@dataclass
class XiaohongshuNoteBrief:
    note_id, xsec_token, title, author_info, statistic, cover_image, ...

@dataclass
class XiaohongshuNoteDetails:
    note_id, title, desc, tags, published_date, ip_location,
    statistic, images, video, timestamp, ...
```

#### 同步函数
- `_sync_single_xiaohongshu_note_brief()`: 单个笔记简要信息同步
- `_update_single_xiaohongshu_note_details()`: 单个笔记详情更新
- `sync_xiaohongshu_collections_list()`: 同步收藏夹列表
- `sync_notes_in_xiaohongshu_collection()`: 同步收藏夹内笔记
- `sync_xiaohongshu_notes_details()`: 批量同步笔记详情

### 5. API 端点（`backend/app/api/endpoints/sync.py`）

添加了三个主要端点（与B站接口对称）：

```
POST /api/v1/sync/xiaohongshu/collections
- 同步小红书收藏夹列表
- Request: SyncCollectionsRequest { max_collections?: int }
- Response: SyncCollectionsResponse

POST /api/v1/sync/xiaohongshu/collections/{collection_id}/notes
- 同步指定收藏夹内的笔记列表
- Request: SyncNotesInCollectionRequest { max_notes?: int }
- Response: SyncNotesInCollectionResponse

POST /api/v1/sync/xiaohongshu/notes/details
- 批量同步笔记详情
- Request: SyncNoteDetailsRequest { note_ids: List[str] }
- Response: SyncNoteDetailsResponse
```

### 6. Executor 支持（`backend/app/services/executors.py`）

扩展了 `SourceTextBuilder` 类：

```python
# 新增方法
.add_xiaohongshu_metadata()      # 添加发布地点、时间、统计数据
.add_xiaohongshu_images()         # 添加图片信息
.add_xiaohongshu_video()          # 添加视频信息
```

更新了 `_build_source_text()` 函数：
- 平台检测逻辑
- 针对小红书的警告信息
- 平台特定的内容构建流程

### 7. 配置（`backend/app/core/config.py`）

添加小红书配置项：
```python
XIAOHONGSHU_COOKIE_IDS: list[str]
XIAOHONGSHU_FAVORITES_PLUGIN_ID: str = "xiaohongshu_favorites_brief"
XIAOHONGSHU_STREAM_INTERVAL: int = 120
```

## 统一的接口设计

前端可以使用统一的 Schema 处理 B站和小红书数据：

### FavoriteItem 统一结构
```typescript
interface FavoriteItem {
  id: number
  platform: "bilibili" | "xiaohongshu"
  item_type: "video" | "note"
  title: string
  intro: string
  cover_url: string
  author: Author
  tags: Tag[]

  // 平台特定详情（可选）
  bilibili_video_details?: BilibiliVideoDetail
  xiaohongshu_note_details?: XiaohongshuNoteDetail

  results: Result[]
  created_at: string
  favorited_at: string
}
```

### 统一的同步流程

无论是B站还是小红书，都遵循相同的三步流程：

1. **同步收藏夹列表**
   ```bash
   POST /api/v1/sync/{platform}/collections
   ```

2. **同步收藏夹内容（简要）**
   ```bash
   POST /api/v1/sync/{platform}/collections/{id}/{items}
   # B站: .../videos
   # 小红书: .../notes
   ```

3. **同步详细信息**
   ```bash
   POST /api/v1/sync/{platform}/{items}/details
   # B站: .../videos/details
   # 小红书: .../notes/details
   ```

## 测试建议

### 1. 数据库迁移测试
```bash
cd backend
# 删除旧数据库（开发环境）
rm mindecho1.db

# 启动服务器（自动创建表）
uvicorn app.main:app --reload
```

### 2. API 测试

#### 同步收藏夹列表
```bash
curl -X POST http://localhost:8000/api/v1/sync/xiaohongshu/collections \
  -H "Content-Type: application/json" \
  -d '{"max_collections": 10}'
```

#### 同步笔记列表
```bash
curl -X POST http://localhost:8000/api/v1/sync/xiaohongshu/collections/{collection_id}/notes \
  -H "Content-Type: application/json" \
  -d '{"max_notes": 20}'
```

#### 同步笔记详情
```bash
curl -X POST http://localhost:8000/api/v1/sync/xiaohongshu/notes/details \
  -H "Content-Type: application/json" \
  -d '{"note_ids": ["note123", "note456"]}'
```

### 3. Workshop 测试

小红书内容可以直接使用现有的 Workshop：

```bash
# 执行工作坊任务
curl -X POST http://localhost:8000/api/v1/workshops/summary-01/execute \
  -H "Content-Type: application/json" \
  -d '{"collection_id": <note_favorite_item_id>}'
```

## 前端集成建议

### 1. 统一的 API 客户端

```typescript
// app/lib/api.ts
export const syncService = {
  // 通用同步方法
  async syncCollections(platform: 'bilibili' | 'xiaohongshu', maxItems?: number) {
    return api.post(`/sync/${platform}/collections`, { max_collections: maxItems })
  },

  async syncCollectionItems(
    platform: 'bilibili' | 'xiaohongshu',
    collectionId: string,
    maxItems?: number
  ) {
    const itemType = platform === 'bilibili' ? 'videos' : 'notes'
    const paramKey = platform === 'bilibili' ? 'max_videos' : 'max_notes'
    return api.post(`/sync/${platform}/collections/${collectionId}/${itemType}`, {
      [paramKey]: maxItems
    })
  },

  async syncItemDetails(
    platform: 'bilibili' | 'xiaohongshu',
    itemIds: string[]
  ) {
    const itemType = platform === 'bilibili' ? 'videos' : 'notes'
    const paramKey = platform === 'bilibili' ? 'bvids' : 'note_ids'
    return api.post(`/sync/${platform}/${itemType}/details`, {
      [paramKey]: itemIds
    })
  }
}
```

### 2. 平台检测组件

```vue
<template>
  <div>
    <!-- B站内容 -->
    <div v-if="item.platform === 'bilibili' && item.bilibili_video_details">
      <p>时长: {{ item.bilibili_video_details.duration_sec }}秒</p>
      <p>播放: {{ item.bilibili_video_details.view_count }}</p>
    </div>

    <!-- 小红书内容 -->
    <div v-if="item.platform === 'xiaohongshu' && item.xiaohongshu_note_details">
      <p>点赞: {{ item.xiaohongshu_note_details.like_count }}</p>
      <p>收藏: {{ item.xiaohongshu_note_details.collect_count }}</p>
      <div v-if="item.xiaohongshu_note_details.images.length > 0">
        <img
          v-for="img in item.xiaohongshu_note_details.images"
          :key="img.id"
          :src="img.image_url"
        />
      </div>
    </div>
  </div>
</template>
```

## 未来扩展

此架构为添加更多平台（YouTube、Twitter、RSS等）提供了清晰的模板：

1. 在 `models.py` 添加平台特定的 Detail 模型
2. 在 `schemas/unified.py` 添加 Pydantic schemas
3. 在 `favorites_service.py` 添加同步函数
4. 在 `sync.py` 添加 API 端点
5. 在 `executors.py` 添加平台特定的内容构建器
6. 在 `config.py` 添加平台配置

## 检查清单

- [x] 数据库模型完整
- [x] Pydantic Schemas 完整
- [x] CRUD 操作更新
- [x] 同步服务实现
- [x] API 端点添加
- [x] Executor 支持
- [x] 配置添加
- [x] 文档编写

## 注意事项

1. **环境变量**: 确保在 `.env` 文件中设置 `XIAOHONGSHU_COOKIE_IDS`
2. **RPC 插件**: 确保 RPC 服务支持以下插件 ID：
   - `xiaohongshu_collection_list`
   - `xiaohongshu_favorites_brief`
   - `xiaohongshu_details`
3. **数据库迁移**: 首次使用需要重建数据库或运行迁移
4. **错误处理**: 所有同步函数都包含完整的错误处理和日志记录

## 总结

小红书集成已完全按照 MindEcho 的最佳实践实现，与 B站集成保持对称性，前端可以使用统一的接口和数据结构处理两个平台的内容。
