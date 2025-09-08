<script setup lang="ts">
import { ref } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { FileText, Video, Sparkles, Clock, ExternalLink } from 'lucide-vue-next'

const outputs = ref([
  {
    id: 1,
    title: '2024年前端技术趋势深度解析',
    type: 'summary',
    source: 'Vue 3 生态系统演进',
    time: '10分钟前',
    workshop: '精华摘要',
    preview: '本文深入探讨了Vue 3在2024年的发展方向，包括性能优化、开发体验提升以及生态系统的完善...',
  },
  {
    id: 2,
    title: 'AI辅助编程的利弊权衡',
    type: 'insight',
    source: 'GitHub Copilot vs Cursor',
    time: '25分钟前',
    workshop: '观点对撞',
    preview: '通过对比分析不同AI编程助手的优劣，探讨了AI在编程领域的应用边界和未来发展...',
  },
  {
    id: 3,
    title: 'React与Vue框架对比研究',
    type: 'analysis',
    source: '前端框架深度对比',
    time: '1小时前',
    workshop: '信息炼金术',
    preview: '综合多篇技术文章，系统性地比较了React和Vue在架构设计、性能表现、学习曲线等方面的差异...',
  },
  {
    id: 4,
    title: 'TypeScript类型系统最佳实践',
    type: 'summary',
    source: 'TS高级特性详解',
    time: '2小时前',
    workshop: '精华摘要',
    preview: '总结了TypeScript类型系统的高级用法，包括条件类型、映射类型、模板字面量类型等...',
  },
])

const typeConfig = {
  summary: {
    label: '摘要',
    color: 'bg-blue-500/10 text-blue-500',
    icon: FileText,
  },
  insight: {
    label: '洞察',
    color: 'bg-purple-500/10 text-purple-500',
    icon: Sparkles,
  },
  analysis: {
    label: '分析',
    color: 'bg-green-500/10 text-green-500',
    icon: Video,
  },
}
</script>

<template>
  <Card class="h-full flex flex-col">
    <CardHeader class="pb-4">
      <div class="flex items-center justify-between">
        <CardTitle class="text-lg">最新成果</CardTitle>
        <NuxtLink to="/outputs" class="text-sm text-primary hover:underline flex items-center gap-1">
          查看全部
          <ExternalLink class="w-3 h-3" />
        </NuxtLink>
      </div>
    </CardHeader>
    <CardContent class="flex-1 overflow-hidden">
      <div class="space-y-4 h-full overflow-y-auto pr-1 -mr-1">
        <div
          v-for="output in outputs"
          :key="output.id"
          class="group relative bg-card p-4 rounded-lg border border-border hover:border-primary/50 transition-all duration-200 cursor-pointer hover:shadow-md"
        >
          <!-- Header -->
          <div class="flex items-start justify-between mb-2">
            <div class="flex-1 pr-2">
              <h4 class="font-medium text-sm line-clamp-1 group-hover:text-primary transition-colors">
                {{ output.title }}
              </h4>
              <p class="text-xs text-muted-foreground mt-1">
                来源: {{ output.source }}
              </p>
            </div>
            <Badge :class="typeConfig[output.type].color" class="text-xs">
              <component :is="typeConfig[output.type].icon" class="w-3 h-3 mr-1" />
              {{ typeConfig[output.type].label }}
            </Badge>
          </div>
          
          <!-- Preview -->
          <p class="text-sm text-muted-foreground line-clamp-2 mb-3">
            {{ output.preview }}
          </p>
          
          <!-- Footer -->
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center gap-3 text-muted-foreground">
              <span class="font-medium">{{ output.workshop }}</span>
              <span>•</span>
              <div class="flex items-center gap-1">
                <Clock class="w-3 h-3" />
                <span>{{ output.time }}</span>
              </div>
            </div>
            <div class="opacity-0 group-hover:opacity-100 transition-opacity">
              <ExternalLink class="w-4 h-4 text-primary" />
            </div>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<style scoped>
/* Custom scrollbar */
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