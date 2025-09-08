<script setup lang="ts">
import { computed } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, FlaskConical, Swords, BookOpen, Zap, TrendingUp } from 'lucide-vue-next'

const dashboardStore = useDashboardStore()

const workshopIdToComponent = {
  'snapshot-insight': { icon: Activity, color: 'text-blue-500', bgColor: 'bg-blue-500/10' },
  'information-alchemy': { icon: FlaskConical, color: 'text-purple-500', bgColor: 'bg-purple-500/10' },
  'point-counterpoint': { icon: Swords, color: 'text-orange-500', bgColor: 'bg-orange-500/10' },
  'summary-01': { icon: BookOpen, color: 'text-green-500', bgColor: 'bg-green-500/10' },
}

const workshops = computed(() => {
  const status = dashboardStore.workshopsStatus
  if (!status) return []

  return Object.entries(status).map(([id, data]) => {
    const config = workshopIdToComponent[id] || { icon: Zap, color: 'text-gray-500', bgColor: 'bg-gray-500/10' }
    const name = id.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()); // Simple name generation
    
    return {
      id,
      name,
      active: data.active,
      completed: data.completed,
      ...config,
      trend: [3, 5, 2, 8, 7, 9, 6], // Mock trend data
    }
  })
})

const maxTrendValue = computed(() => {
  if (!workshops.value.length) return 1
  return Math.max(...workshops.value.flatMap(w => w.trend))
})
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
      <div v-if="workshops.length" class="grid grid-cols-2 gap-4">
        <div
          v-for="workshop in workshops"
          :key="workshop.id"
          class="group relative p-4 rounded-lg border border-border hover:border-primary/50 transition-all duration-200 cursor-pointer hover:shadow-md"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="flex items-center gap-3">
              <div :class="[workshop.bgColor, 'p-2 rounded-lg']">
                <component :is="workshop.icon" :class="[workshop.color, 'w-5 h-5']" />
              </div>
              <div>
                <h4 class="font-medium text-sm">{{ workshop.name }}</h4>
                <p class="text-xs text-muted-foreground">
                  总计 {{ workshop.completed }} 次
                </p>
              </div>
            </div>
          </div>
          
          <div v-if="workshop.active > 0" 
            class="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 bg-primary/10 rounded-full">
            <div class="w-2 h-2 bg-primary rounded-full animate-pulse" />
            <span class="text-xs font-medium text-primary">{{ workshop.active }} 进行中</span>
          </div>
          
          <div class="mt-4">
            <div class="flex items-end gap-1 h-12">
              <div
                v-for="(value, index) in workshop.trend"
                :key="index"
                class="flex-1 bg-muted rounded-t transition-all duration-300 hover:bg-primary/20"
                :style="{ height: `${(value / maxTrendValue) * 100}%` }"
              />
            </div>
            <div class="flex items-center justify-between mt-2 text-xs text-muted-foreground">
              <span>7天趋势</span>
              <div class="flex items-center gap-1">
                <TrendingUp class="w-3 h-3 text-green-500" />
                <span>+12%</span> <!-- Mock trend change -->
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-8 text-muted-foreground">
        <Zap class="w-8 h-8 mx-auto mb-2" />
        <p class="text-sm">暂无工坊数据。</p>
      </div>
    </CardContent>
  </Card>
</template>