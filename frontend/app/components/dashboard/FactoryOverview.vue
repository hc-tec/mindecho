<script setup lang="ts">
import { computed } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, FileText, Brain, Sparkles } from 'lucide-vue-next'

const dashboardStore = useDashboardStore()

const overview = computed(() => dashboardStore.overview)

const stats = computed(() => [
  { label: '总收藏', value: overview.value?.total_items || 0, icon: FileText, change: '+12%' }, // Note: 'change' is mock data
  { label: 'AI 处理', value: overview.value?.processed_items || 0, icon: Brain, change: '+23%' },
  { label: '待处理', value: overview.value?.pending_items || 0, icon: Sparkles, change: '+5%' },
])

const heatmapData = computed(() => dashboardStore.activityHeatmap || [])
const maxValue = computed(() => {
  if (!heatmapData.value.length) return 1
  return Math.max(...heatmapData.value.map(d => d.count))
})

const getHeatmapColor = (count: number) => {
  if (count === 0) return 'bg-muted'
  const intensity = count / maxValue.value
  if (intensity < 0.25) return 'bg-primary/20'
  if (intensity < 0.5) return 'bg-primary/40'
  if (intensity < 0.75) return 'bg-primary/60'
  return 'bg-primary'
}

const distribution = computed(() => {
  if (!overview.value) return []
  const platformCounts = overview.value.items_by_platform || {}
  const total = Object.values(platformCounts).reduce((sum, count) => sum + count, 0)
  if (total === 0) return []
  
  return Object.entries(platformCounts).map(([platform, count]) => ({
    name: platform,
    value: count,
    percentage: Math.round((count / total) * 100),
  })).sort((a, b) => b.value - a.value)
})
</script>

<template>
  <Card class="h-full">
    <CardHeader class="pb-4">
      <div class="flex items-center justify-between">
        <CardTitle class="text-xl">数据工厂总览</CardTitle>
        <div class="flex items-center text-sm text-muted-foreground">
          <TrendingUp class="w-4 h-4 mr-1 text-green-500" />
          <span>本月增长 28%</span> <!-- Mock data -->
        </div>
      </div>
    </CardHeader>
    <CardContent class="space-y-6">
      <!-- Stats Grid -->
      <div class="grid grid-cols-3 gap-4">
        <div v-for="stat in stats" :key="stat.label" class="relative group cursor-pointer">
          <div class="p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors duration-200">
            <div class="flex items-center justify-between mb-2">
              <component :is="stat.icon" class="w-5 h-5 text-muted-foreground" />
              <span class="text-xs font-medium text-green-500">{{ stat.change }}</span> <!-- Mock data -->
            </div>
            <div class="space-y-1">
              <p class="text-2xl font-semibold tracking-tight">{{ stat.value }}</p>
              <p class="text-xs text-muted-foreground">{{ stat.label }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Activity Heatmap -->
      <div>
        <h4 class="text-sm font-medium mb-3">30天活动热力图</h4>
        <div v-if="heatmapData.length" class="flex gap-1 flex-wrap">
          <div v-for="day in heatmapData" :key="day.date" class="relative group">
            <div 
              :class="[
                'w-5 h-5 rounded-sm transition-all duration-200 cursor-pointer',
                getHeatmapColor(day.count),
                'hover:scale-110 hover:shadow-lg'
              ]"
            />
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
              {{ day.date }}: {{ day.count }} 项
            </div>
          </div>
        </div>
        <div v-else class="text-sm text-muted-foreground">
          暂无活动数据。
        </div>
      </div>

      <!-- Distribution Chart -->
      <div>
        <h4 class="text-sm font-medium mb-3">内容分布</h4>
        <div class="space-y-3">
          <div v-for="(item, index) in distribution" :key="item.name" class="space-y-2">
            <div class="flex items-center justify-between text-sm">
              <span class="capitalize">{{ item.name }}</span>
              <span class="text-muted-foreground">{{ item.percentage }}%</span>
            </div>
            <div class="h-2 bg-muted rounded-full overflow-hidden">
              <div 
                :class="['h-full rounded-full transition-all duration-500', `bg-primary/${100 - (index * 20)}`]"
                :style="{ width: `${item.percentage}%` }" 
              />
            </div>
          </div>
          <div v-if="!distribution.length" class="text-sm text-muted-foreground">
            暂无内容分布数据。
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>
