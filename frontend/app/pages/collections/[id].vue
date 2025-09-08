<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useCollectionsStore } from '@/stores/collections'
import { useWorkshopsStore } from '@/stores/workshops'
import { computed, onMounted, ref } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { format } from 'date-fns'
import { Link, Tag, User, Clock, Loader2, Sparkles, AlertTriangle } from 'lucide-vue-next'

const route = useRoute()
const collectionsStore = useCollectionsStore()
const workshopsStore = useWorkshopsStore()

const itemId = Number(route.params.id)
const activeTaskIds = ref<string[]>([])

const item = computed(() => collectionsStore.activeItem)
const workshops = computed(() => workshopsStore.workshops)
const tasks = computed(() => workshopsStore.tasks)
const isLoading = computed(() => collectionsStore.loading || workshopsStore.loading)

onMounted(() => {
  collectionsStore.fetchCollectionById(itemId)
  workshopsStore.fetchWorkshops()
})

const handleExecuteWorkshop = async (workshopId: string) => {
  const taskId = await workshopsStore.executeWorkshop(workshopId, itemId)
  if (taskId) {
    activeTaskIds.value.push(taskId)
    workshopsStore.subscribeToTask(taskId)
  }
}

const getTaskForWorkshop = (workshopId: string) => {
  return Object.values(tasks.value).find(t => t.workshop_id === workshopId && t.favorite_item_id === itemId)
}
</script>

<template>
  <div v-if="isLoading && !item" class="flex items-center justify-center h-full">
    <Loader2 class="w-12 h-12 animate-spin text-primary" />
  </div>
  <div v-else-if="item" class="h-full grid grid-cols-1 md:grid-cols-3 gap-4 p-4">
    <!-- Left Column: Details -->
    <div class="md:col-span-1 space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{{ item.title }}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <p class="text-sm text-muted-foreground">{{ item.description }}</p>
          <div class="flex items-center gap-2">
            <User class="w-4 h-4" />
            <span class="text-sm font-medium">{{ item.author_name }}</span>
          </div>
          <div class="flex items-center gap-2">
            <Clock class="w-4 h-4" />
            <span class="text-sm">{{ format(new Date(item.favorited_at), 'yyyy-MM-dd HH:mm') }}</span>
          </div>
          <div class="flex items-center gap-2">
            <Link class="w-4 h-4" />
            <a :href="item.url" target="_blank" class="text-sm text-primary hover:underline">
              Go to source
            </a>
          </div>
          <div class="flex flex-wrap gap-2">
            <Badge v-for="tag in item.tags" :key="tag.id" variant="secondary">{{ tag.name }}</Badge>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Right Column: Workshops & Results -->
    <div class="md:col-span-2 space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>AI Workshops</CardTitle>
        </CardHeader>
        <CardContent class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card v-for="workshop in workshops" :key="workshop.id" class="bg-muted/50">
            <CardHeader>
              <CardTitle class="text-base">{{ workshop.name }}</CardTitle>
            </CardHeader>
            <CardContent>
              <p class="text-sm text-muted-foreground mb-4 h-10">{{ workshop.description }}</p>
              <Button @click="handleExecuteWorkshop(workshop.id)" class="w-full">
                <Sparkles class="w-4 h-4 mr-2" />
                Execute
              </Button>
            </CardContent>
          </Card>
        </CardContent>
      </Card>
      
      <Card v-for="taskId in activeTaskIds" :key="taskId">
        <CardHeader>
          <CardTitle>Result for: {{ tasks[taskId]?.workshop_id }}</CardTitle>
        </CardHeader>
        <CardContent>
          <div v-if="tasks[taskId] && tasks[taskId].status === 'in_progress'" class="flex items-center gap-2">
            <Loader2 class="w-4 h-4 animate-spin" />
            <span>Processing...</span>
          </div>
          <div v-else-if="tasks[taskId] && tasks[taskId].status === 'success'">
            <p class="text-sm prose dark:prose-invert">{{ tasks[taskId].result?.content }}</p>
          </div>
          <div v-else-if="tasks[taskId] && tasks[taskId].status === 'failure'" class="text-destructive flex items-center gap-2">
            <AlertTriangle class="w-4 h-4" />
            <span>{{ tasks[taskId].error || 'An unknown error occurred.' }}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
