<script setup lang="ts">
/**
 * 最近输出组件
 *
 * 展示最新的 AI 生成结果：
 * - 工坊名称和图标
 * - 输出内容预览（前150字符）
 * - 创建时间（相对时间）
 * - 展开/折叠功能
 *
 * 数据来源：dashboardStore.recentOutputs
 *
 * 设计特点：
 * - 响应式卡片列表
 * - 内容预览和展开切换
 * - 优雅的悬浮效果
 * - 空状态友好提示
 */

import { computed, ref } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FileText, ChevronDown, ChevronUp, Sparkles } from 'lucide-vue-next'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

const dashboardStore = useDashboardStore()

// ============================================================================
// 数据访问
// ============================================================================

/**
 * 最近的 AI 输出结果列表
 * 按创建时间降序排列
 */
const recentOutputs = computed(() => dashboardStore.recentOutputs)

// ============================================================================
// 展开/折叠状态管理
// ============================================================================

/**
 * 记录每个输出的展开状态
 * key: output.id, value: boolean (是否展开)
 */
const expandedItems = ref<Record<number, boolean>>({})

/**
 * 切换指定输出的展开状态
 */
const toggleExpand = (id: number) => {
  expandedItems.value[id] = !expandedItems.value[id]
}

/**
 * 检查指定输出是否已展开
 */
const isExpanded = (id: number) => {
  return expandedItems.value[id] || false
}

// ============================================================================
// 内容预览逻辑
// ============================================================================

/**
 * 获取内容预览
 * 如果内容长度超过150字符，截断并添加省略号
 */
const getContentPreview = (content: string, isExpanded: boolean) => {
  if (!content) return '无内容'
  if (isExpanded || content.length <= 150) return content
  return content.substring(0, 150) + '...'
}

/**
 * 判断内容是否需要显示展开按钮
 */
const shouldShowExpandButton = (content: string) => {
  return content && content.length > 150
}

// ============================================================================
// 时间格式化
// ============================================================================

/**
 * 格式化相对时间
 * 将 ISO 时间字符串转换为中文相对时间描述
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
</script>

<template>
  <Card class="h-full flex flex-col">
    <CardHeader class="pb-4">
      <div class="flex items-center justify-between">
        <CardTitle class="text-lg">最近输出</CardTitle>
        <FileText class="w-4 h-4 text-muted-foreground" />
      </div>
    </CardHeader>

    <CardContent class="flex-1 overflow-hidden">
      <!-- 可滚动的输出列表 -->
      <div class="h-full overflow-y-auto space-y-4 pr-1 -mr-1">
        <!-- 输出卡片 -->
        <div
          v-for="output in recentOutputs"
          :key="output.id"
          class="p-4 rounded-lg border border-border hover:border-primary/50 transition-all duration-200 hover:shadow-md"
        >
          <!-- 输出头部：工坊ID + 时间 -->
          <div class="flex items-center justify-between mb-3">
            <Badge variant="outline" class="text-xs">
              {{ output.workshop_id }}
            </Badge>
            <span class="text-xs text-muted-foreground">
              {{ formatRelativeTime(output.created_at) }}
            </span>
          </div>

          <!-- 输出内容 -->
          <div class="space-y-2">
            <p
              class="text-sm leading-relaxed"
              :class="{ 'line-clamp-3': !isExpanded(output.id) }"
            >
              {{ getContentPreview(output.content, isExpanded(output.id)) }}
            </p>

            <!-- 展开/折叠按钮 -->
            <Button
              v-if="shouldShowExpandButton(output.content)"
              variant="ghost"
              size="sm"
              class="h-auto py-1 px-2 text-xs"
              @click="toggleExpand(output.id)"
            >
              <component
                :is="isExpanded(output.id) ? ChevronUp : ChevronDown"
                class="w-3 h-3 mr-1"
              />
              {{ isExpanded(output.id) ? '收起' : '展开' }}
            </Button>
          </div>
        </div>

        <!-- 空状态 -->
        <div
          v-if="recentOutputs.length === 0"
          class="h-full flex flex-col items-center justify-center text-center p-6"
        >
          <div class="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
            <Sparkles class="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 class="font-medium mb-1">暂无输出</h3>
          <p class="text-sm text-muted-foreground">
            AI 工坊还未生成任何内容
          </p>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<style scoped>
/**
 * 自定义滚动条样式
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
