<script setup lang="ts">
/**
 * 数据工厂总览组件
 *
 * 展示系统核心统计数据：
 * - 三个关键指标：总收藏、AI处理、待处理
 * - 活动热力图：最近30天的收藏活动可视化
 * - 内容分布：按平台（Bilibili、小红书）的内容占比
 * - AI 工坊矩阵：所有工坊的运行状态和活跃度
 *
 * 数据来源：dashboardStore.overviewStats, dashboardStore.workshopMatrix
 */

import { computed } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, FileText, Brain, Sparkles, Activity, FlaskConical, Swords, BookOpen, Zap } from 'lucide-vue-next'

const dashboardStore = useDashboardStore()

// ============================================================================
// 数据访问
// ============================================================================

const overviewStats = computed(() => dashboardStore.overviewStats)
const heatmapData = computed(() => dashboardStore.activityHeatmap)
const workshopMatrix = computed(() => dashboardStore.workshopMatrix)

// ============================================================================
// 关键指标卡片配置
// ============================================================================

const stats = computed(() => [
  {
    label: '总收藏',
    value: overviewStats.value?.total_items || 0,
    icon: FileText,
    growthText: `${overviewStats.value?.recent_growth.toFixed(1) || 0}%`
  },
  {
    label: 'AI 处理',
    value: overviewStats.value?.processed_items || 0,
    icon: Brain,
    growthText: `${dashboardStore.processingPercentage}%`
  },
  {
    label: '待处理',
    value: overviewStats.value?.pending_items || 0,
    icon: Sparkles,
    growthText: '-'
  },
])

// ============================================================================
// 活动热力图逻辑
// ============================================================================

/**
 * 计算热力图中的最大值，用于颜色强度归一化
 */
const maxValue = computed(() => {
  if (!heatmapData.value.length) return 1
  return Math.max(...heatmapData.value.map(d => d.count))
})

/**
 * 根据活动数量计算热力图方块的颜色
 *
 * 使用分级策略：
 * - count = 0: 灰色（无活动）
 * - intensity < 0.25: 淡蓝色
 * - intensity < 0.5: 中蓝色
 * - intensity < 0.75: 深蓝色
 * - intensity >= 0.75: 最深蓝色
 */
const getHeatmapColor = (count: number) => {
  if (count === 0) return 'bg-muted'
  const intensity = count / maxValue.value
  if (intensity < 0.25) return 'bg-primary/20'
  if (intensity < 0.5) return 'bg-primary/40'
  if (intensity < 0.75) return 'bg-primary/60'
  return 'bg-primary'
}

// ============================================================================
// 平台分布逻辑
// ============================================================================

/**
 * 平台显示名称映射（中文本地化）
 */
const platformDisplayNames: Record<string, string> = {
  bilibili: '哔哩哔哩',
  xiaohongshu: '小红书'
}

/**
 * 计算平台分布数据（百分比和排序）
 *
 * 转换格式：{ bilibili: 100, xiaohongshu: 50 }
 * → [{ name: '哔哩哔哩', value: 100, percentage: 67 }, ...]
 *
 * 按数量降序排列
 */
const distribution = computed(() => {
  if (!overviewStats.value) return []

  const platformCounts = overviewStats.value.items_by_platform
  const total = Object.values(platformCounts).reduce((sum, count) => sum + count, 0)

  if (total === 0) return []

  return Object.entries(platformCounts)
    .map(([platform, count]) => ({
      name: platformDisplayNames[platform] || platform,
      value: count,
      percentage: Math.round((count / total) * 100),
    }))
    .sort((a, b) => b.value - a.value)  // 降序
})

// ============================================================================
// 工坊矩阵逻辑
// ============================================================================

/**
 * 工坊 ID 到图标和颜色的映射
 * 为每个工坊提供独特的视觉识别
 */
const workshopVisualConfig: Record<string, {
  icon: any
  color: string
  bgColor: string
}> = {
  'snapshot-insight': {
    icon: Activity,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10'
  },
  'information-alchemy': {
    icon: FlaskConical,
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10'
  },
  'point-counterpoint': {
    icon: Swords,
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10'
  },
  'summary-01': {
    icon: BookOpen,
    color: 'text-green-500',
    bgColor: 'bg-green-500/10'
  },
  'learning-tasks': {
    icon: Zap,
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10'
  }
}

/**
 * 获取工坊的视觉配置
 * 如果工坊 ID 未配置，返回默认的灰色配置
 */
const getWorkshopConfig = (workshopId: string) => {
  return workshopVisualConfig[workshopId] || {
    icon: Zap,
    color: 'text-gray-500',
    bgColor: 'bg-gray-500/10'
  }
}

/**
 * 计算所有工坊7天活动中的最大值
 * 用于归一化趋势图的高度
 */
const maxTrendValue = computed(() => {
  if (!workshopMatrix.value.length) return 1

  const allValues = workshopMatrix.value.flatMap(w => w.activity_last_7_days)
  const max = Math.max(...allValues)

  return max > 0 ? max : 1  // 避免除以0
})

/**
 * 计算趋势柱的高度百分比
 */
const getTrendHeight = (value: number) => {
  return (value / maxTrendValue.value) * 100
}
</script>

<template>
  <Card class="h-full">
    <CardHeader class="pb-4">
      <div class="flex items-center justify-between">
        <CardTitle class="text-xl">数据工厂总览</CardTitle>
        <div v-if="overviewStats" class="flex items-center text-sm text-muted-foreground">
          <TrendingUp class="w-4 h-4 mr-1" :class="overviewStats.recent_growth >= 0 ? 'text-green-500' : 'text-red-500'" />
          <span>
            最近30天 {{ overviewStats.recent_growth >= 0 ? '+' : '' }}{{ overviewStats.recent_growth.toFixed(1) }}%
          </span>
        </div>
      </div>
    </CardHeader>

    <CardContent class="space-y-6">
      <!-- 三个关键指标 -->
      <div class="grid grid-cols-3 gap-4">
        <div v-for="stat in stats" :key="stat.label" class="relative group cursor-pointer">
          <div class="p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors duration-200">
            <div class="flex items-center justify-between mb-2">
              <component :is="stat.icon" class="w-5 h-5 text-muted-foreground" />
              <span class="text-xs font-medium text-green-500">{{ stat.growthText }}</span>
            </div>
            <div class="space-y-1">
              <p class="text-2xl font-semibold tracking-tight">{{ stat.value }}</p>
              <p class="text-xs text-muted-foreground">{{ stat.label }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 活动热力图 -->
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
            <!-- Tooltip -->
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10 shadow-lg border border-border">
              {{ day.date }}: {{ day.count }} 项
            </div>
          </div>
        </div>
        <div v-else class="text-sm text-muted-foreground">
          暂无活动数据。开始收藏内容后，这里将显示你的活动热力图。
        </div>
      </div>

      <!-- 平台内容分布 -->
      <div>
        <h4 class="text-sm font-medium mb-3">内容分布</h4>
        <div class="space-y-3">
          <div v-for="(item, index) in distribution" :key="item.name" class="space-y-2">
            <div class="flex items-center justify-between text-sm">
              <span class="font-medium">{{ item.name }}</span>
              <span class="text-muted-foreground">{{ item.value }} 项 ({{ item.percentage }}%)</span>
            </div>
            <div class="h-2 bg-muted rounded-full overflow-hidden">
              <div
                :class="['h-full rounded-full transition-all duration-500', index === 0 ? 'bg-primary' : 'bg-primary/70']"
                :style="{ width: `${item.percentage}%` }"
              />
            </div>
          </div>
          <div v-if="!distribution.length" class="text-sm text-muted-foreground">
            暂无内容分布数据。
          </div>
        </div>
      </div>

      <!-- AI 工坊矩阵 -->
      <div>
        <h4 class="text-sm font-medium mb-3">AI 工坊矩阵</h4>

        <!-- 工坊网格 -->
        <div v-if="workshopMatrix.length" class="grid grid-cols-2 gap-3">
          <div
            v-for="workshop in workshopMatrix"
            :key="workshop.id"
            class="group relative p-3 rounded-lg border border-border hover:border-primary/50 transition-all duration-200 cursor-pointer hover:shadow-md"
          >
            <!-- 工坊头部：图标 + 名称 + 统计 -->
            <div class="flex items-start justify-between mb-3">
              <div class="flex items-center gap-2">
                <!-- 工坊图标 -->
                <div :class="[getWorkshopConfig(workshop.id).bgColor, 'p-1.5 rounded-lg']">
                  <component
                    :is="getWorkshopConfig(workshop.id).icon"
                    :class="[getWorkshopConfig(workshop.id).color, 'w-4 h-4']"
                  />
                </div>

                <!-- 工坊名称和统计 -->
                <div>
                  <h5 class="font-medium text-xs">{{ workshop.name }}</h5>
                  <p class="text-xs text-muted-foreground">
                    总计 {{ workshop.total }} 次
                  </p>
                </div>
              </div>
            </div>

            <!-- 进行中任务徽章（仅当有任务时显示） -->
            <div
              v-if="workshop.in_progress > 0"
              class="absolute top-2 right-2 flex items-center gap-1 px-1.5 py-0.5 bg-primary/10 rounded-full"
            >
              <div class="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" />
              <span class="text-xs font-medium text-primary">
                {{ workshop.in_progress }}
              </span>
            </div>

            <!-- 7天趋势图 -->
            <div class="mt-2">
              <!-- 柱状图 -->
              <div class="flex items-end gap-0.5 h-8">
                <div
                  v-for="(value, index) in workshop.activity_last_7_days"
                  :key="index"
                  class="flex-1 bg-muted rounded-t transition-all duration-300 hover:bg-primary/20 relative group/bar"
                  :style="{ height: `${getTrendHeight(value)}%` }"
                  :title="`${value} 个任务`"
                >
                  <!-- Tooltip（悬浮时显示） -->
                  <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-1.5 py-0.5 bg-popover text-popover-foreground text-xs rounded opacity-0 group-hover/bar:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10 shadow-lg border border-border">
                    {{ value }}
                  </div>
                </div>
              </div>

              <!-- 图例 -->
              <div class="flex items-center justify-between mt-1.5 text-xs text-muted-foreground">
                <span>7天</span>
                <span>{{ workshop.activity_last_7_days.reduce((a, b) => a + b, 0) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="text-center py-6 text-muted-foreground">
          <Zap class="w-6 h-6 mx-auto mb-2" />
          <p class="text-xs">暂无工坊数据。</p>
        </div>
      </div>
    </CardContent>
  </Card>
</template>
