/**
 * Dashboard Store
 *
 * 管理仪表盘数据的状态和更新：
 * - 从后端获取完整的仪表盘数据
 * - 提供响应式的 getter 用于组件访问数据
 * - 实现智能刷新策略（防止频繁请求）
 *
 * 设计原则：
 * - 单一数据源：一次 API 调用获取所有数据
 * - 响应式设计：使用 Pinia getters 提供计算属性
 * - 性能优先：30秒内不重复刷新
 */

import { defineStore } from 'pinia'
import { api } from '@/lib/api'
import type { DashboardResponse, OverviewStats, ActivityDay, WorkshopMatrixItem, FavoriteItem, Result, TrendingKeyword } from '@/types/api'

interface DashboardState {
  data: DashboardResponse | null
  loading: boolean
  error: string | null
  lastUpdated: Date | null
}

export const useDashboardStore = defineStore('dashboard', {
  state: (): DashboardState => ({
    data: null,
    loading: false,
    error: null,
    lastUpdated: null,
  }),

  getters: {
    /**
     * 总览统计数据
     * 包含：总收藏数、已处理数、待处理数、平台分布、增长率
     */
    overviewStats: (state): OverviewStats | null => state.data?.overview_stats || null,

    /**
     * 活动热力图数据
     * 最近30天每天的收藏数量
     */
    activityHeatmap: (state): ActivityDay[] => state.data?.activity_heatmap || [],

    /**
     * 待处理队列
     * 最近的待处理项目列表
     */
    pendingQueue: (state): FavoriteItem[] => state.data?.pending_queue || [],

    /**
     * 工坊矩阵
     * 每个工坊的统计和最近7天活动
     */
    workshopMatrix: (state): WorkshopMatrixItem[] => state.data?.workshop_matrix || [],

    /**
     * 最近输出
     * 最新的 AI 生成结果
     */
    recentOutputs: (state): Result[] => state.data?.recent_outputs || [],

    /**
     * 趋势关键词
     * 最热门的标签/关键词
     */
    trendingKeywords: (state): TrendingKeyword[] => state.data?.trending_keywords || [],

    // ========================================================================
    // 便捷的计算属性（从 overviewStats 派生）
    // ========================================================================

    /**
     * 总收藏数
     */
    totalItems: (state): number => state.data?.overview_stats.total_items || 0,

    /**
     * 已处理数
     */
    processedItems: (state): number => state.data?.overview_stats.processed_items || 0,

    /**
     * 待处理数
     */
    pendingItems: (state): number => state.data?.overview_stats.pending_items || 0,

    /**
     * 按平台分布
     */
    itemsByPlatform: (state) => state.data?.overview_stats.items_by_platform || { bilibili: 0, xiaohongshu: 0 },

    /**
     * 最近增长率（百分比）
     */
    recentGrowth: (state): number => state.data?.overview_stats.recent_growth || 0,

    /**
     * 处理进度百分比
     * 计算公式：(已处理数 / 总收藏数) * 100
     */
    processingPercentage: (state): number => {
      const total = state.data?.overview_stats.total_items || 0
      const processed = state.data?.overview_stats.processed_items || 0
      return total > 0 ? Math.round((processed / total) * 100) : 0
    },
  },

  actions: {
    /**
     * 从后端获取仪表盘数据
     *
     * 发起 API 请求，更新 store 状态
     * 设置 loading 和 error 状态，记录更新时间
     */
    async fetchDashboard() {
      this.loading = true
      this.error = null

      try {
        const data = await api.get<DashboardResponse>('/dashboard')
        this.data = data
        this.lastUpdated = new Date()
      } catch (error) {
        this.error = error instanceof Error ? error.message : '获取仪表盘数据失败'
        console.error('Dashboard fetch error:', error)
      } finally {
        this.loading = false
      }
    },

    /**
     * 智能刷新仪表盘数据
     *
     * 防止频繁刷新的策略：
     * - 如果正在加载，直接返回
     * - 如果距离上次更新不足30秒，直接返回
     * - 否则执行刷新
     *
     * 用于自动刷新场景（如定时轮询）
     */
    async refreshDashboard() {
      // 防止并发刷新
      if (this.loading) return

      // 防止频繁刷新（30秒限制）
      if (this.lastUpdated) {
        const timeSinceUpdate = Date.now() - this.lastUpdated.getTime()
        if (timeSinceUpdate < 30000) return
      }

      await this.fetchDashboard()
    },

    /**
     * 清除错误状态
     *
     * 用于用户手动关闭错误提示
     */
    clearError() {
      this.error = null
    },
  },
})
