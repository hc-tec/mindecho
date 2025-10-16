/**
 * API 类型定义
 *
 * 与后端 schemas/unified.py 保持完全一致
 * 确保前后端类型安全和数据结构统一
 */

// ============================================================================
// Dashboard Types (与后端 DashboardResponse schema 对应)
// ============================================================================

/**
 * 按平台统计的项目数量
 */
export interface PlatformStats {
  bilibili: number
  xiaohongshu: number
}

/**
 * 仪表盘总览统计数据
 *
 * 包含系统核心指标：
 * - total_items: 总收藏数（所有 FavoriteItem）
 * - processed_items: 已处理数（有成功 Result 的项）
 * - pending_items: 待处理数（status = PENDING 的项）
 * - items_by_platform: 按平台分布的项目数
 * - recent_growth: 最近30天的增长百分比
 */
export interface OverviewStats {
  total_items: number
  processed_items: number
  pending_items: number
  items_by_platform: PlatformStats
  recent_growth: number  // 百分比，例如 28.5 表示 28.5%
}

/**
 * 单日活动数据
 *
 * 用于生成活动热力图，记录每天的收藏数量
 */
export interface ActivityDay {
  date: string  // ISO format: "2024-01-01"
  count: number  // 当日收藏数
}

/**
 * 工坊矩阵单项数据
 *
 * 展示单个工坊的运行状态和活跃度：
 * - id: workshop_id
 * - name: 工坊名称
 * - total: 历史总输出数（Result 总数）
 * - in_progress: 当前进行中的任务数
 * - activity_last_7_days: 最近7天每天的任务创建数（从旧到新）
 */
export interface WorkshopMatrixItem {
  id: string
  name: string
  total: number
  in_progress: number
  activity_last_7_days: number[]  // 7个整数，从7天前到今天
}

/**
 * 趋势关键词
 *
 * 从标签中提取的高频词，用于发现用户收藏的内容趋势
 */
export interface TrendingKeyword {
  keyword: string
  frequency: number  // 出现频次
}

/**
 * 仪表盘完整响应数据
 *
 * 聚合所有仪表盘组件需要的数据，一次请求返回所有信息
 * 以提高前端性能和用户体验
 */
export interface DashboardResponse {
  overview_stats: OverviewStats
  activity_heatmap: ActivityDay[]
  pending_queue: FavoriteItem[]
  workshop_matrix: WorkshopMatrixItem[]
  recent_outputs: Result[]
  trending_keywords: TrendingKeyword[]
}

export interface FavoriteItem {
  id: number
  platform_item_id: string
  platform: string
  title: string
  intro?: string
  cover_url?: string
  published_at?: string
  favorited_at: string
  status: 'pending' | 'processed' | 'failed'
  // Derived for convenience
  author_name?: string
  url?: string
  description?: string
  author?: {
    platform_user_id: string
    platform: string
    username: string
    avatar_url?: string
    id: number
  }
  collection?: Collection | null
  tags: Tag[]
}

export interface Collection {
  id: number
  platform_collection_id: string
  platform: string
  name: string
  description?: string
  cover_url?: string
  item_count: number
  created_at: string
  updated_at: string
}

export interface Tag {
  id: number
  name: string
  created_at: string
}

export interface Result {
  id: number
  favorite_item_id: number
  workshop_id: string
  content: string
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
  favorite_item?: FavoriteItem
}

export interface Workshop {
  // Backend unified schema
  id: number
  workshop_id: string
  name: string
  description?: string
  default_prompt: string
  default_model?: string
  executor_type: string
  executor_config?: Record<string, any> | null

  // Legacy compatible fields (optional)
  type?: string
  system_prompt?: string
  user_prompt_template?: string
  model?: string
  temperature?: number
  max_tokens?: number
  config?: Record<string, any>
}

export interface Task {
  id: string
  favorite_item_id: number
  workshop_id: string
  status: 'pending' | 'in_progress' | 'success' | 'failure'
  created_at: string
  completed_at?: string
  error?: string
  // While streaming, we may only have partial fields; always allow content-only
  result?: Partial<Result> & { content?: string }
}

export interface PaginatedResponse<T> {
  total: number
  items: T[]
}

export interface Settings {
  theme: 'light' | 'dark'
  notifications_enabled: boolean
  ai_model: string
  sync_interval: number
  auto_process: boolean
  category_to_workshop?: Record<string, string>
}

// ============================================================================
// Notification Config Types
// ============================================================================

/**
 * Processor configuration for text formatting and image rendering
 */
export interface ProcessorConfig {
  text_format: 'markdown' | 'plain' | 'html'
  max_length: number | null
  add_header: boolean
  add_footer: boolean
  render_image: boolean
  image_style: string
  image_size: string
}

/**
 * Workshop notification configuration
 */
export interface NotificationConfig {
  id: number
  workshop_id: string
  enabled: boolean
  processors: string[]
  notifier_type: 'local_storage' | 'email'
  processor_config: ProcessorConfig
  notifier_config: Record<string, any>
  created_at: string
  updated_at: string
}

/**
 * Request payload for creating notification config
 */
export interface NotificationConfigCreate {
  workshop_id: string
  enabled: boolean
  processors: string[]
  notifier_type: 'local_storage' | 'email'
  processor_config: ProcessorConfig
  notifier_config: Record<string, any>
}

/**
 * Request payload for updating notification config
 */
export interface NotificationConfigUpdate {
  enabled?: boolean
  processors?: string[]
  notifier_type?: 'local_storage' | 'email'
  processor_config?: ProcessorConfig
  notifier_config?: Record<string, any>
}
