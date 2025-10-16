# 工作坊智能路由解决方案

## 问题描述

收藏项都是通过工作坊监听来获取的，但收藏项不知道应该属于哪个工作坊。之前所有收藏项点击后都默认跳转到 `summary-01` 工作坊，这在多个工作坊开启监听时会造成混乱。

## 解决方案

### 核心思路

通过 **Platform Bindings（平台绑定）** 机制，将收藏项所属的 Collection（收藏夹）与工作坊关联起来：

1. 每个工作坊可以绑定多个平台的多个收藏夹
2. 收藏项属于某个收藏夹
3. 根据收藏项的收藏夹ID和平台，查找绑定了该收藏夹的工作坊
4. 点击收藏项时，智能跳转到绑定的工作坊

### 数据结构

**工作坊配置（executor_config）：**
```json
{
  "platform_bindings": [
    {
      "platform": "bilibili",
      "collection_ids": [1, 2, 3]
    },
    {
      "platform": "xiaohongshu",
      "collection_ids": [4, 5]
    }
  ],
  "listening_enabled": true
}
```

**收藏项（FavoriteItem）：**
```typescript
{
  id: 123,
  platform: "bilibili",
  collection: {
    id: 2,
    name: "深度思考",
    platform: "bilibili"
  },
  // ... 其他字段
}
```

## 前端实现

### 1. Workshops Store 新增方法

**文件：** `frontend/app/stores/workshops.ts:228-268`

#### `getWorkshopByCollection(collectionId, platform)`
根据收藏夹ID和平台查找绑定的工作坊。

**逻辑：**
1. 遍历所有工作坊
2. 检查 `executor_config.platform_bindings`
3. 查找匹配的平台和collection_ids
4. 返回第一个匹配的工作坊

#### `getDefaultWorkshop()`
获取默认工作坊（fallback机制）。

**优先级：**
1. 返回 `summary-01` 工作坊（如果存在）
2. 返回第一个工作坊
3. 返回 null

### 2. 智能路由函数

在所有收藏项列表页面添加智能路由函数：

```typescript
const navigateToWorkshop = (item: FavoriteItem) => {
  let workshopId = 'summary-01' // 默认工作坊

  // 如果item有collection信息，尝试查找绑定的工作坊
  if (item.collection?.id && item.platform) {
    const boundWorkshop = workshopsStore.getWorkshopByCollection(
      item.collection.id,
      item.platform
    )

    if (boundWorkshop) {
      workshopId = boundWorkshop.workshop_id
    } else {
      // 使用默认工作坊
      const defaultWorkshop = workshopsStore.getDefaultWorkshop()
      if (defaultWorkshop) {
        workshopId = defaultWorkshop.workshop_id
      }
    }
  }

  router.push(`/workshops/${workshopId}?item=${item.id}`)
}
```

### 3. 修改的页面

#### ✅ collections.vue（收藏管理页）
- 添加智能路由函数
- 替换硬编码的 `/workshops/summary-01` 跳转
- 添加控制台日志以便调试

#### ✅ inbox.vue（收件箱页）
- 添加智能路由函数
- 图片和标题点击都使用智能路由

#### ✅ collections/[id].vue（收藏详情页）
- 添加智能路由函数
- "在工作坊中查看"按钮使用智能路由

## 使用场景

### 场景1：单个工作坊监听单个收藏夹

**配置：**
- 工作坊A 绑定 Bilibili收藏夹"深度思考"（ID: 1）

**行为：**
- 点击"深度思考"中的任何视频 → 跳转到工作坊A

### 场景2：单个工作坊监听多个收藏夹

**配置：**
- 工作坊A 绑定 Bilibili收藏夹1、2、3

**行为：**
- 点击收藏夹1、2、3中的任何视频 → 跳转到工作坊A

### 场景3：多个工作坊监听不同收藏夹

**配置：**
- 工作坊A（快照洞察）绑定 Bilibili收藏夹"深度思考"（ID: 1）
- 工作坊B（信息炼金术）绑定 Bilibili收藏夹"学习资料"（ID: 2）

**行为：**
- 点击"深度思考"中的视频 → 跳转到工作坊A（快照洞察）
- 点击"学习资料"中的视频 → 跳转到工作坊B（信息炼金术）

### 场景4：收藏项没有绑定工作坊（Fallback）

**配置：**
- 收藏夹3没有被任何工作坊绑定

**行为：**
- 点击收藏夹3中的视频 → 跳转到默认工作坊（summary-01）

### 场景5：跨平台绑定

**配置：**
- 工作坊A 绑定：
  - Bilibili收藏夹1、2
  - 小红书收藏夹4、5

**行为：**
- 点击Bilibili收藏夹1的视频 → 跳转到工作坊A
- 点击小红书收藏夹4的笔记 → 跳转到工作坊A
- 点击Bilibili收藏夹3的视频 → 跳转到默认工作坊

## 后端支持

### API Endpoints（已存在）

#### GET `/api/v1/workshops/manage/{workshop_id}/platform-bindings`
获取工作坊的平台绑定配置。

**响应：**
```json
{
  "platform_bindings": [
    {
      "platform": "bilibili",
      "collection_ids": [1, 2, 3]
    }
  ],
  "listening_enabled": true
}
```

#### PUT `/api/v1/workshops/manage/{workshop_id}/platform-bindings`
更新工作坊的平台绑定配置。

**请求体：**
```json
{
  "platform_bindings": [
    {
      "platform": "bilibili",
      "collection_ids": [1, 2, 3]
    },
    {
      "platform": "xiaohongshu",
      "collection_ids": [4, 5]
    }
  ]
}
```

### 数据存储

Platform bindings 存储在 `workshops` 表的 `executor_config` 字段中（JSON格式）。

## 优势

1. **灵活性**：一个工作坊可以监听多个收藏夹，支持多平台
2. **可扩展性**：轻松添加新平台和新工作坊
3. **用户友好**：自动跳转到正确的工作坊，减少困惑
4. **Fallback机制**：未绑定的收藏项自动使用默认工作坊
5. **向后兼容**：如果没有配置绑定，仍然能正常工作

## 调试

在控制台查看路由决策日志：

```javascript
// collections.vue
console.log(`Found bound workshop: ${workshopId} for collection ${item.collection.name}`)
console.log(`No bound workshop found, using default: ${workshopId}`)
```

## 未来改进

1. **UI可视化配置**：在设置页面提供工作坊绑定的可视化配置界面
2. **绑定优先级**：当多个工作坊绑定同一收藏夹时，支持优先级配置
3. **智能推荐**：根据收藏项的标签、内容自动推荐合适的工作坊
4. **绑定统计**：显示每个工作坊处理了多少来自不同收藏夹的内容

## 总结

通过 Platform Bindings 机制，成功解决了收藏项与工作坊的关联问题。用户现在可以：

- ✅ 为不同收藏夹配置不同的工作坊
- ✅ 点击收藏项时自动跳转到正确的工作坊
- ✅ 支持多平台、多收藏夹的灵活绑定
- ✅ 享受智能fallback机制，不会出现找不到工作坊的情况
