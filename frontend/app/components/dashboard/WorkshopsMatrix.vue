<script setup lang="ts">
/**
 * AI 工坊矩阵组件
 *
 * 展示所有工坊的运行状态和活跃度：
 * - 工坊图标和名称
 * - 历史总输出数（总执行次数）
 * - 当前进行中的任务数
 * - 最近7天的活动趋势图
 *
 * 数据来源：dashboardStore.workshopMatrix
 *
 * 设计特点：
 * - 响应式网格布局（2列）
 * - 动态高度的趋势柱状图
 * - 进行中任务的脉冲动画
 * - 悬浮效果增强交互
 */

import { computed } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, FlaskConical, Swords, BookOpen, Zap } from 'lucide-vue-next'

const dashboardStore = useDashboardStore()

// ============================================================================
// 数据访问
// ============================================================================

/**
 * 工坊矩阵数据
 * 包含每个工坊的统计信息和7天活动趋势
 */
const workshopMatrix = computed(() => dashboardStore.workshopMatrix)

// ============================================================================
// 工坊视觉配置
// ============================================================================

/**
 * 工坊 ID 到图标和颜色的映射
 *
 * 为每个工坊提供独特的视觉识别：
 * - snapshot-insight: 蓝色 Activity 图标
 * - information-alchemy: 紫色烧瓶图标
 * - point-counterpoint: 橙色剑图标
 * - summary-01: 绿色书本图标
 * - 其他: 灰色闪电图标（fallback）
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

// ============================================================================
// 趋势图逻辑
// ============================================================================

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
 *
 * @param value - 当天的活动数
 * @returns 高度百分比（0-100）
 */
const getTrendHeight = (value: number) => {
  return (value / maxTrendValue.value) * 100
}
</script>

<template>
  <Card class="h-full">
    <CardHeader class="pb-4">
      <div class="flex items-center justify-between">
        <CardTitle class="text-lg">AI 工坊矩阵</CardTitle>
        <Zap class="w-4 h-4 text-muted-foreground" />
      </div>
    </CardHeader>

    <CardContent>
      <!-- 工坊网格 -->
      <div v-if="workshopMatrix.length" class="grid grid-cols-2 gap-4">
        <div
          v-for="workshop in workshopMatrix"
          :key="workshop.id"
          class="group relative p-4 rounded-lg border border-border hover:border-primary/50 transition-all duration-200 cursor-pointer hover:shadow-md"
        >
          <!-- 工坊头部：图标 + 名称 + 统计 -->
          <div class="flex items-start justify-between mb-3">
            <div class="flex items-center gap-3">
              <!-- 工坊图标 -->
              <div :class="[getWorkshopConfig(workshop.id).bgColor, 'p-2 rounded-lg']">
                <component
                  :is="getWorkshopConfig(workshop.id).icon"
                  :class="[getWorkshopConfig(workshop.id).color, 'w-5 h-5']"
                />
              </div>

              <!-- 工坊名称和统计 -->
              <div>
                <h4 class="font-medium text-sm">{{ workshop.name }}</h4>
                <p class="text-xs text-muted-foreground">
                  总计 {{ workshop.total }} 次
                </p>
              </div>
            </div>
          </div>

          <!-- 进行中任务徽章（仅当有任务时显示） -->
          <div
            v-if="workshop.in_progress > 0"
            class="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 bg-primary/10 rounded-full"
          >
            <div class="w-2 h-2 bg-primary rounded-full animate-pulse" />
            <span class="text-xs font-medium text-primary">
              {{ workshop.in_progress }} 进行中
            </span>
          </div>

          <!-- 7天趋势图 -->
          <div class="mt-4">
            <!-- 柱状图 -->
            <div class="flex items-end gap-1 h-12">
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
            <div class="flex items-center justify-between mt-2 text-xs text-muted-foreground">
              <span>最近7天</span>
              <span>{{ workshop.activity_last_7_days.reduce((a, b) => a + b, 0) }} 个任务</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="text-center py-8 text-muted-foreground">
        <Zap class="w-8 h-8 mx-auto mb-2" />
        <p class="text-sm">暂无工坊数据。</p>
      </div>
    </CardContent>
  </Card>
</template>
