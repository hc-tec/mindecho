<script setup lang="ts">
/**
 * 趋势洞察组件
 *
 * 展示最热门的标签/关键词：
 * - 关键词名称
 * - 出现频次
 * - 简洁的趋势图标
 *
 * 数据来源：dashboardStore.trendingKeywords
 *
 * 设计特点：
 * - 简洁的列表展示
 * - 悬浮效果增强交互
 * - 空状态友好提示
 */

import { computed } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, Hash } from 'lucide-vue-next'

const dashboardStore = useDashboardStore()

// ============================================================================
// 数据访问
// ============================================================================

/**
 * 趋势关键词列表
 * 按频次降序排列
 */
const trendingKeywords = computed(() => dashboardStore.trendingKeywords)
</script>

<template>
  <Card class="h-full flex flex-col">
    <CardHeader class="pb-4">
      <div class="flex items-center justify-between">
        <CardTitle class="text-lg">趋势洞察</CardTitle>
        <TrendingUp class="w-4 h-4 text-muted-foreground" />
      </div>
    </CardHeader>

    <CardContent class="flex-1 overflow-hidden">
      <!-- 可滚动的关键词列表 -->
      <div class="h-full overflow-y-auto pr-1 -mr-1">
        <div class="space-y-3">
          <!-- 关键词卡片 -->
          <div
            v-for="(keyword, index) in trendingKeywords"
            :key="index"
            class="group flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-all duration-200 cursor-pointer"
          >
            <!-- 左侧：图标 + 关键词 + 频次 -->
            <div class="flex items-center gap-3 flex-1 min-w-0">
              <!-- 图标 -->
              <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <Hash class="w-4 h-4 text-primary" />
              </div>

              <!-- 关键词信息 -->
              <div class="min-w-0 flex-1">
                <h4 class="font-medium text-sm group-hover:text-primary transition-colors truncate">
                  {{ keyword.keyword }}
                </h4>
                <p class="text-xs text-muted-foreground">
                  {{ keyword.frequency }} 次提及
                </p>
              </div>
            </div>

            <!-- 右侧：趋势图标 -->
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-green-500 text-sm font-medium">
                ↑
              </span>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div
          v-if="trendingKeywords.length === 0"
          class="h-full flex flex-col items-center justify-center text-center p-6"
        >
          <div class="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
            <TrendingUp class="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 class="font-medium mb-1">暂无趋势数据</h3>
          <p class="text-sm text-muted-foreground">
            收藏内容添加标签后，这里将展示热门话题
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
