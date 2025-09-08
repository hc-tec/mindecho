<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Clock, GripVertical, ArrowRight } from 'lucide-vue-next'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

const dashboardStore = useDashboardStore()
const pendingItems = computed(() => dashboardStore.pendingQueue)

const typeColors = {
  video: 'bg-blue-500/10 text-blue-500',
  article: 'bg-green-500/10 text-green-500',
  other: 'bg-gray-500/10 text-gray-500',
}

const formatRelativeTime = (dateString: string) => {
  if (!dateString) return ''
  return formatDistanceToNow(new Date(dateString), { addSuffix: true, locale: zhCN })
}

// Drag state - this would be implemented with a library like VueDraggable
const draggedItem = ref<number | null>(null)
</script>

<template>
  <Card class="h-full flex flex-col">
    <CardHeader class="pb-4">
      <div class="flex items-center justify-between">
        <CardTitle class="text-lg">待处理队列</CardTitle>
        <Badge v-if="pendingItems.length > 0" variant="secondary" class="text-xs">
          {{ pendingItems.length }} 项
        </Badge>
      </div>
    </CardHeader>
    <CardContent class="flex-1 overflow-hidden">
      <div class="h-full overflow-y-auto space-y-3 pr-1 -mr-1">
        <div
          v-for="item in pendingItems"
          :key="item.id"
          class="group relative bg-card rounded-lg border transition-all duration-200 cursor-move hover:border-primary/50 hover:shadow-md"
          :draggable="true"
        >
          <div class="p-4">
            <div class="absolute left-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
              <GripVertical class="w-4 h-4 text-muted-foreground" />
            </div>
            
            <div class="pl-4">
              <div class="flex items-start justify-between mb-2">
                <h4 class="font-medium text-sm line-clamp-2 pr-2">
                  {{ item.title }}
                </h4>
                <Badge :class="typeColors[item.platform] || typeColors.other" class="text-xs shrink-0 capitalize">
                  {{ item.platform }}
                </Badge>
              </div>
              
              <div class="flex items-center gap-3 text-xs text-muted-foreground">
                <div class="flex items-center gap-1">
                  <Clock class="w-3 h-3" />
                  <span>{{ formatRelativeTime(item.favorited_at) }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
            <ArrowRight class="w-4 h-4 text-muted-foreground" />
          </div>
        </div>
        
        <div v-if="pendingItems.length === 0" 
          class="h-full flex flex-col items-center justify-center text-center p-6">
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