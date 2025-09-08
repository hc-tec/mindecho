<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useWorkshopsStore } from '@/stores/workshops'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useRouter } from 'vue-router'

const store = useWorkshopsStore()
const router = useRouter()

onMounted(() => {
  store.fetchWorkshops()
})

const workshops = computed(() => store.workshops)
const isLoading = computed(() => store.loading)

const goToWorkshop = (workshopId: string) => {
  router.push(`/workshops/${workshopId}`)
}
</script>

<template>
  <div class="h-full flex flex-col">
    <header class="p-4 border-b border-border bg-muted/50">
      <h2 class="text-2xl font-bold tracking-tight">AI 工作坊</h2>
      <p class="text-muted-foreground">选择一个工作坊来处理您的收藏或输入。</p>
    </header>

    <div class="flex-1 overflow-y-auto p-8">
      <div v-if="isLoading" class="text-center text-muted-foreground">
        <p>正在加载工作坊...</p>
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card 
          v-for="workshop in workshops" 
          :key="workshop.workshop_id" 
          class="flex flex-col hover:shadow-lg transition-shadow"
        >
          <CardHeader>
            <CardTitle>{{ workshop.name }}</CardTitle>
            <CardDescription class="line-clamp-3 h-[60px]">{{ workshop.description }}</CardDescription>
          </CardHeader>
          <CardContent class="flex-1 flex items-end">
            <Button @click="goToWorkshop(workshop.workshop_id)" class="w-full">
              进入工作坊
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>
