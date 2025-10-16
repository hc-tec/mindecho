<script setup lang="ts">
/**
 * 待处理队列组件
 *
 * 展示最近的待处理项目列表，提供：
 * - 项目标题和平台标识
 * - 收藏时间（相对时间格式）
 * - 拖拽手柄和悬浮效果
 * - 空状态提示
 *
 * 数据来源：dashboardStore.pendingQueue
 *
 * 设计特点：
 * - 响应式高度，自动滚动
 * - 优雅的悬浮交互效果
 * - 清晰的视觉层次
 */

import { computed, ref } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Clock, GripVertical, ArrowRight } from 'lucide-vue-next'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

const dashboardStore = useDashboardStore()

// ============================================================================
// 数据访问
// ============================================================================

/**
 * 待处理项目列表
 * 从 dashboard store 获取最近的待处理收藏
 */
const pendingItems = computed(() => dashboardStore.pendingQueue)

// ============================================================================
// 视觉样式配置
// ============================================================================

/**
 * 平台标签颜色映射
 *
 * 为不同平台提供视觉区分：
 * - bilibili: 蓝色
 * - xiaohongshu: 红色
 * - 其他: 灰色
 */
const platformColors: Record<string, string> = {
  bilibili: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  xiaohongshu: 'bg-red-500/10 text-red-500 border-red-500/20',
}

/**
 * 获取平台标签的样式类
 */
const getPlatformColor = (platform: string) => {
  return platformColors[platform] || 'bg-muted text-muted-foreground'
}

// ============================================================================
// 时间格式化
// ============================================================================

/**
 * 格式化相对时间
 *
 * 将 ISO 时间字符串转换为中文相对时间描述
 * 例如："2小时前"、"3天前"
 *
 * @param dateString - ISO 格式的时间字符串
 * @returns 中文相对时间描述
 */
const formatRelativeTime = (dateString: string) => {
  if (!dateString) return ''
  try {
    return formatDistanceToNow(new Date(dateString), {
      addSuffix: true,
      locale: zhCN
    })
  } catch (error) {
    console.error('Time formatting error:', error)
    return ''
  }
}

// ============================================================================
// 拖拽状态（未来功能预留）
// ============================================================================

/**
 * 当前拖拽的项目 ID
 * 预留用于未来实现拖拽排序功能
 */
const draggedItem = ref<number | null>(null)
</script>

<template>
  <Card class="h-full flex flex-col">
    <CardHeader class="pb-4">
      <div class="flex items-center justify-between">
        <CardTitle class="text-lg">待处理队列</CardTitle>
        <!-- 项目数量徽章 -->
        <Badge v-if="pendingItems.length > 0" variant="secondary" class="text-xs">
          {{ pendingItems.length }} 项
        </Badge>
      </div>
    </CardHeader>

    <CardContent class="flex-1 overflow-hidden">
      <!-- 可滚动的项目列表 -->
      <div class="h-full overflow-y-auto space-y-3 pr-1 -mr-1">
        <!-- 待处理项目卡片 -->
        <div
          v-for="item in pendingItems"
          :key="item.id"
          class="group relative bg-card rounded-lg border transition-all duration-200 cursor-pointer hover:border-primary/50 hover:shadow-md"
          :draggable="true"
        >
          <div class="p-4">
            <!-- 拖拽手柄（悬浮时显示） -->
            <div class="absolute left-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
              <GripVertical class="w-4 h-4 text-muted-foreground" />
            </div>

            <div class="pl-4">
              <!-- 标题和平台标签 -->
              <div class="flex items-start justify-between mb-2">
                <h4 class="font-medium text-sm line-clamp-2 pr-2 flex-1">
                  {{ item.title }}
                </h4>
                <Badge
                  :class="getPlatformColor(item.platform)"
                  class="text-xs shrink-0 capitalize"
                >
                  {{ item.platform }}
                </Badge>
              </div>

              <!-- 收藏时间 -->
              <div class="flex items-center gap-3 text-xs text-muted-foreground">
                <div class="flex items-center gap-1">
                  <Clock class="w-3 h-3" />
                  <span>{{ formatRelativeTime(item.favorited_at) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 箭头指示器（悬浮时显示） -->
          <div class="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
            <ArrowRight class="w-4 h-4 text-muted-foreground" />
          </div>
        </div>

        <!-- 空状态 -->
        <div
          v-if="pendingItems.length === 0"
          class="h-full flex flex-col items-center justify-center text-center p-6"
        >
          <div class="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
            <Clock class="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 class="font-medium mb-1">队列已清空</h3>
          <p class="text-sm text-muted-foreground">
            所有内容都已处理完成
          </p>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<style scoped>
/**
 * 自定义滚动条样式
 *
 * 提供更精致的滚动条外观：
 * - 细窄的滚动条（6px）
 * - 圆角滑块
 * - 悬浮时深色高亮
 */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  @apply bg-muted rounded-full;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-muted-foreground/30;
}
</style>
