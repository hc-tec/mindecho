<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, Hash } from 'lucide-vue-next'

const keywords = ref([
  { text: 'Vue 3', count: 42, trend: 'up' },
  { text: 'TypeScript', count: 38, trend: 'up' },
  { text: 'AI 编程', count: 35, trend: 'up' },
  { text: 'Tailwind CSS', count: 28, trend: 'stable' },
  { text: '前端架构', count: 24, trend: 'up' },
  { text: 'React 18', count: 22, trend: 'down' },
  { text: '性能优化', count: 20, trend: 'up' },
  { text: 'Next.js', count: 18, trend: 'stable' },
])

// Auto-scroll logic
const containerRef = ref<HTMLElement>()
let scrollInterval: number

const startAutoScroll = () => {
  scrollInterval = setInterval(() => {
    if (containerRef.value) {
      containerRef.value.scrollTop += 1
      // Reset to top when reaching bottom
      if (containerRef.value.scrollTop >= containerRef.value.scrollHeight - containerRef.value.clientHeight) {
        containerRef.value.scrollTop = 0
      }
    }
  }, 50) as unknown as number
}

const stopAutoScroll = () => {
  clearInterval(scrollInterval)
}

onMounted(() => {
  startAutoScroll()
})

onUnmounted(() => {
  stopAutoScroll()
})

const getTrendIcon = (trend: string) => {
  if (trend === 'up') return '↑'
  if (trend === 'down') return '↓'
  return '→'
}

const getTrendColor = (trend: string) => {
  if (trend === 'up') return 'text-green-500'
  if (trend === 'down') return 'text-red-500'
  return 'text-yellow-500'
}
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
      <div 
        ref="containerRef"
        class="h-full overflow-hidden hover:overflow-y-auto transition-all"
        @mouseenter="stopAutoScroll"
        @mouseleave="startAutoScroll"
      >
        <div class="space-y-3 pb-4">
          <div
            v-for="(keyword, index) in keywords"
            :key="index"
            class="group flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-all duration-200 cursor-pointer"
          >
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Hash class="w-4 h-4 text-primary" />
              </div>
              <div>
                <h4 class="font-medium text-sm group-hover:text-primary transition-colors">
                  {{ keyword.text }}
                </h4>
                <p class="text-xs text-muted-foreground">
                  {{ keyword.count }} 次提及
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span :class="[getTrendColor(keyword.trend), 'text-sm font-medium']">
                {{ getTrendIcon(keyword.trend) }}
              </span>
              <div class="w-12 h-6">
                <svg class="w-full h-full" viewBox="0 0 48 24">
                  <path
                    v-if="keyword.trend === 'up'"
                    d="M 4 20 L 12 16 L 20 18 L 28 12 L 36 8 L 44 4"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    class="text-green-500"
                  />
                  <path
                    v-else-if="keyword.trend === 'down'"
                    d="M 4 4 L 12 8 L 20 6 L 28 12 L 36 16 L 44 20"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    class="text-red-500"
                  />
                  <path
                    v-else
                    d="M 4 12 L 44 12"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    class="text-yellow-500"
                  />
                </svg>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Fade effect at bottom -->
        <div class="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-background to-transparent pointer-events-none" />
      </div>
    </CardContent>
  </Card>
</template>

<style scoped>
/* Smooth scrolling */
.overflow-hidden {
  scroll-behavior: smooth;
}

/* Hide scrollbar when auto-scrolling */
.overflow-hidden::-webkit-scrollbar {
  width: 0;
}

/* Show scrollbar on hover */
.hover\:overflow-y-auto:hover::-webkit-scrollbar {
  width: 6px;
}

.hover\:overflow-y-auto:hover::-webkit-scrollbar-track {
  background: transparent;
}

.hover\:overflow-y-auto:hover::-webkit-scrollbar-thumb {
  @apply bg-muted rounded-full;
}

.hover\:overflow-y-auto:hover::-webkit-scrollbar-thumb:hover {
  @apply bg-muted-foreground/30;
}
</style>