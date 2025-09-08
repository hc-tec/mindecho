import { defineStore } from 'pinia'
import { api } from '@/lib/api'
import type { DashboardResponse } from '@/types/api'

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
    overview: (state) => state.data?.overview || null,
    activityHeatmap: (state) => state.data?.activity_heatmap || [],
    pendingQueue: (state) => state.data?.pending_queue || [],
    workshopsStatus: (state) => state.data?.workshops_status || {},
    recentOutputs: (state) => state.data?.recent_outputs || [],
    trendingTags: (state) => state.data?.trending_tags || [],
    
    totalItems: (state) => state.data?.overview.total_items || 0,
    processedItems: (state) => state.data?.overview.processed_items || 0,
    pendingItems: (state) => state.data?.overview.pending_items || 0,
    
    processingPercentage: (state) => {
      const total = state.data?.overview.total_items || 0
      const processed = state.data?.overview.processed_items || 0
      return total > 0 ? Math.round((processed / total) * 100) : 0
    },
  },

  actions: {
    async fetchDashboard() {
      this.loading = true
      this.error = null
      
      try {
        const data = await api.get<DashboardResponse>('/dashboard')
        this.data = data
        this.lastUpdated = new Date()
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to fetch dashboard data'
        console.error('Dashboard fetch error:', error)
      } finally {
        this.loading = false
      }
    },

    async refreshDashboard() {
      // Don't refresh if already loading
      if (this.loading) return
      
      // Only refresh if last update was more than 30 seconds ago
      if (this.lastUpdated) {
        const timeSinceUpdate = Date.now() - this.lastUpdated.getTime()
        if (timeSinceUpdate < 30000) return
      }
      
      await this.fetchDashboard()
    },

    clearError() {
      this.error = null
    },
  },
})
