// API Types based on backend schemas

export interface DashboardResponse {
  overview: {
    total_items: number
    processed_items: number
    pending_items: number
    total_results: number
    items_by_platform: Record<string, number>
    items_by_status: Record<string, number>
  }
  activity_heatmap: Array<{
    date: string
    count: number
  }>
  pending_queue: FavoriteItem[]
  workshops_status: Record<string, {
    active: number
    completed: number
    failed: number
  }>
  recent_outputs: Result[]
  trending_tags: Array<{
    name: string
    count: number
  }>
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
