<script setup lang="ts">
import { useDashboardStore } from '@/stores/dashboard'
import { Loader2, AlertCircle } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import DashboardFactoryOverview from '@/components/dashboard/FactoryOverview.vue'
import DashboardPendingQueue from '@/components/dashboard/PendingQueue.vue'
import DashboardRecentOutputs from '@/components/dashboard/RecentOutputs.vue'
import DashboardTrendSpotting from '@/components/dashboard/TrendSpotting.vue'
import DashboardSystemMonitoring from '@/components/dashboard/SystemMonitoring.vue'
import { useCollectionsStore } from '@/stores/collections'

const dashboardStore = useDashboardStore()
const collectionsStore = useCollectionsStore()

// Fetch dashboard data on mount
onMounted(() => {
  dashboardStore.fetchDashboard()
})

// Auto-refresh every 20 seconds (polling instead of websocket)
const refreshInterval = ref<number>()
onMounted(() => {
  refreshInterval.value = setInterval(() => {
    // poll dashboard and collections
    dashboardStore.refreshDashboard()
    collectionsStore.fetchCollections()
  }, 20000) as unknown as number
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-3xl font-bold tracking-tight">仪表盘</h2>
      <div class="flex items-center gap-2">
        <span v-if="dashboardStore.lastUpdated" class="text-sm text-muted-foreground">
          最后更新: {{ new Date(dashboardStore.lastUpdated).toLocaleTimeString() }}
        </span>
        <Button
          variant="ghost"
          size="sm"
          @click="dashboardStore.fetchDashboard"
          :disabled="dashboardStore.loading"
        >
          <Loader2 v-if="dashboardStore.loading" class="w-4 h-4 animate-spin" />
          <span v-else>刷新</span>
        </Button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="dashboardStore.error" class="mb-6">
      <div class="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive">
        <AlertCircle class="w-5 h-5" />
        <span>{{ dashboardStore.error }}</span>
        <Button
          variant="ghost"
          size="sm"
          class="ml-auto"
          @click="dashboardStore.clearError"
        >
          关闭
        </Button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="dashboardStore.loading && !dashboardStore.data" 
      class="flex items-center justify-center h-96">
      <div class="text-center">
        <Loader2 class="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
        <p class="text-muted-foreground">加载仪表盘数据...</p>
      </div>
    </div>

    <!-- Dashboard Grid -->
    <div v-else class="space-y-6">
      <!-- 第一行：数据工厂总览（含工坊矩阵） + 趋势洞察 -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2">
          <DashboardFactoryOverview />
        </div>
        <DashboardTrendSpotting />
      </div>

      <!-- 第二行：系统监控 + 最近输出 + 待处理队列（紧凑三列） -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <DashboardSystemMonitoring />
        <DashboardRecentOutputs />
        <DashboardPendingQueue />
      </div>
    </div>
  </div>
</template>
