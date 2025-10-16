<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { GripVertical, Plus, Zap, Link, FileText, Sparkles, AlertTriangle } from 'lucide-vue-next'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogClose } from '@/components/ui/dialog'
import { useCollectionsStore } from '@/stores/collections'
import { useWorkshopsStore } from '@/stores/workshops'
import type { Workshop, FavoriteItem } from '@/types/api'
import { api } from '@/lib/api'

const props = defineProps<{
  workshop: Workshop
}>()

const route = useRoute()
const router = useRouter()

// Store and State Management
const collectionsStore = useCollectionsStore()
const workshopsStore = useWorkshopsStore()

const selectedCollection = ref<FavoriteItem | null>(null)
const taskId = ref<string | null>(null)
const editorContent = ref('<h1>合成文档</h1><p>从右侧拖拽 AI 洞察或在此处自由创作...</p>')

const aiInsights = computed(() => {
  if (!taskId.value) return []
  const task = workshopsStore.tasks[taskId.value]
  // TODO: The structure of task.result needs to be confirmed. This is a placeholder.
  // Assuming the result is a JSON object with an 'insights' key containing an array.
  try {
    if (task?.result?.content) {
      const parsedResult = JSON.parse(task.result.content)
      return parsedResult.insights || []
    }
  } catch (e) {
    console.error("Failed to parse AI insights:", e)
  }
  return []
})
const isLoading = computed(() => workshopsStore.loading)
const taskStatus = computed(() => {
    if (!taskId.value) return 'idle'
    return workshopsStore.tasks[taskId.value]?.status || 'pending'
})

onMounted(async () => {
  await collectionsStore.fetchCollections()
  
  // Initialize from URL query if present
  const itemId = route.query.item ? parseInt(route.query.item as string) : null
  if (itemId) {
    try {
      const item = await api.get(`/collections/${itemId}`)
      selectedCollection.value = item
    } catch (error) {
      console.error('Failed to load item from URL:', error)
    }
  }
})

const handleSelectCollection = (collection: FavoriteItem) => {
  selectedCollection.value = collection
  // Update URL
  router.replace({ query: { item: collection.id.toString() } })
}

// Watch for URL query changes
watch(
  () => route.query.item,
  async (itemQuery) => {
    const itemId = itemQuery ? parseInt(itemQuery as string) : null
    if (itemId && (!selectedCollection.value || selectedCollection.value.id !== itemId)) {
      try {
        const item = await api.get(`/collections/${itemId}`)
        selectedCollection.value = item
      } catch (error) {
        console.error('Failed to load item from URL:', error)
      }
    } else if (!itemId) {
      selectedCollection.value = null
    }
  }
)

const handleExecute = async () => {
    if (!selectedCollection.value) return
    const currentId = (props.workshop as any).workshop_id || (props.workshop as any).id
    if (!currentId) return
    const newTaskId = await workshopsStore.executeWorkshop(
        currentId,
        selectedCollection.value.id
    )
    if (newTaskId) {
        taskId.value = newTaskId
        workshopsStore.subscribeToTask(newTaskId)
    }
}

// Placeholder for insight type configuration
const insightConfig: { [key: string]: any } = {
  contradiction: { icon: AlertTriangle, color: 'text-orange-500', label: '潜在矛盾' },
  synthesis: { icon: Sparkles, color: 'text-purple-500', label: '综合观点' },
  question: { icon: Zap, color: 'text-blue-500', label: '关键问题' },
  default: { icon: Sparkles, color: 'text-gray-500', label: '洞察' },
}
const getInsightConfig = (type: string) => insightConfig[type] || insightConfig.default
</script>

<template>
  <div class="fixed inset-0 left-0 md:left-64 flex flex-col bg-background">
    <header class="p-4 border-b border-border bg-muted/50 shrink-0">
      <h2 class="text-2xl font-bold tracking-tight">{{ workshop.name }}</h2>
      <p class="text-muted-foreground">{{ workshop.description }}</p>
    </header>

    <div class="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-px bg-border min-h-0 overflow-hidden">
      <!-- Left Column: Source Materials -->
      <div class="bg-background flex flex-col h-full">
        <div class="p-4 border-b border-border flex items-center justify-between">
          <h3 class="font-semibold">源材料区</h3>
          <Dialog>
            <DialogTrigger as-child>
              <Button size="sm" variant="outline"><Plus class="w-4 h-4 mr-2" /> 
                {{ selectedCollection ? '更换材料' : '选择材料' }}
              </Button>
            </DialogTrigger>
            <DialogContent class="max-w-3xl h-[70vh] flex flex-col">
              <DialogHeader><DialogTitle>选择一个收藏作为源材料</DialogTitle></DialogHeader>
              <ScrollArea class="flex-1 -mx-6 px-6"><div class="space-y-2">
                <DialogClose as-child v-for="item in collectionsStore.items" :key="item.id">
                  <Card @click="handleSelectCollection(item)" class="cursor-pointer hover:bg-muted">
                    <CardContent class="p-3">
                      <p class="font-medium text-sm">{{ item.title }}</p>
                      <p class="text-xs text-muted-foreground capitalize">{{ item.platform }} - {{ item.author?.username || '' }}</p>
                    </CardContent>
                  </Card>
                </DialogClose>
              </div></ScrollArea>
            </DialogContent>
          </Dialog>
        </div>
        <ScrollArea class="flex-1 p-4">
          <div v-if="selectedCollection" class="space-y-3">
            <Card><CardContent class="p-3 flex items-start gap-3">
              <GripVertical class="w-4 h-4 text-muted-foreground mt-1 shrink-0" />
              <div>
                <p class="font-medium text-sm line-clamp-2">{{ selectedCollection.title }}</p>
                <div class="flex items-center gap-1.5 text-xs text-muted-foreground mt-1">
                  <component :is="selectedCollection.platform === 'bilibili' ? Link : FileText" class="w-3 h-3" />
                  <span class="capitalize">{{ selectedCollection.platform }}</span>
                </div>
              </div>
            </CardContent></Card>
          </div>
          <div v-else class="text-center text-muted-foreground p-8 flex flex-col items-center justify-center h-full">
            <p>请先选择一个源材料</p>
          </div>
        </ScrollArea>
        <div v-if="selectedCollection" class="p-4 border-t border-border">
          <Button @click="handleExecute" :disabled="isLoading" class="w-full">
            <Zap class="w-4 h-4 mr-2" />
            {{ isLoading ? `[${taskStatus}] 处理中...` : '执行炼金术' }}
          </Button>
        </div>
      </div>

      <!-- Center Column: Editor -->
      <div class="lg:col-span-2 bg-background flex flex-col h-full">
        <div class="p-4 border-b border-border"><h3 class="font-semibold">炼金台</h3></div>
        <div class="flex-1 overflow-y-auto p-4 prose dark:prose-invert max-w-full" v-html="editorContent" />
      </div>
      
      <!-- Right Column: AI Insights -->
      <div class="bg-background flex flex-col h-full">
        <div class="p-4 border-b border-border"><h3 class="font-semibold">AI 洞察区</h3></div>
        <ScrollArea class="flex-1 p-4">
          <div v-if="taskStatus === 'in_progress' && aiInsights.length === 0" class="text-center text-muted-foreground p-8">
            <p>AI 正在分析, 请稍候...</p>
          </div>
          <div v-else-if="aiInsights.length > 0" class="space-y-3">
            <Card v-for="(insight, index) in aiInsights" :key="index" class="bg-muted/50 cursor-grab active:cursor-grabbing" draggable="true">
              <CardContent class="p-3"><div class="flex items-start gap-3">
                <component :is="getInsightConfig(insight.type).icon" :class="[getInsightConfig(insight.type).color, 'w-4 h-4 mt-1 shrink-0']" />
                <div>
                  <p class="text-xs font-semibold mb-1" :class="getInsightConfig(insight.type).color">{{ getInsightConfig(insight.type).label }}</p>
                  <p class="text-sm">{{ insight.text }}</p>
                </div>
              </div></CardContent>
            </Card>
          </div>
           <div v-else class="text-center text-muted-foreground p-8">
            <p>执行后将在此处生成 AI 洞察</p>
          </div>
        </ScrollArea>
      </div>
    </div>
  </div>
</template>
