<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkshopsStore } from '@/stores/workshops'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useCollectionsStore } from '@/stores/collections'
import type { Workshop } from '@/types/api'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Settings, Maximize2, X, ChevronDown, History } from 'lucide-vue-next'

const props = defineProps<{ workshop: Workshop }>()

const route = useRoute()
const router = useRouter()
const workshopsStore = useWorkshopsStore()
const collectionsStore = useCollectionsStore()

// local editable copies
const name = ref(props.workshop.name)
// Map backend unified fields to local prompts for compatibility
const systemPrompt = ref<string | undefined>((props.workshop as any).default_prompt || props.workshop.system_prompt)
const userPrompt = ref<string | undefined>(props.workshop.user_prompt_template)

// Keep local state in sync if the prop changes (e.g., after fetch)
watch(
  () => props.workshop,
  (wk) => {
    if (!wk) return
    name.value = wk.name
    // prefer unified field
    // @ts-ignore
    systemPrompt.value = (wk as any).default_prompt || (wk as any).system_prompt
    userPrompt.value = (wk as any).user_prompt_template
  },
  { deep: true }
)

const saving = ref(false)
const running = ref(false)
// Initialize from URL query if present
const selectedItemId = ref<number | null>(
  route.query.item ? parseInt(route.query.item as string) : null
)
const activeTaskId = ref<string | null>(null)
const selectedItemDetails = ref<any>(null)
const promptDialogOpen = ref(false)
const resultDetailDialogOpen = ref(false)
const selectedResult = ref<any>(null)
const historyExpanded = ref(false)

const existingResults = computed(() => {
  if (!selectedItemDetails.value?.results) {
    console.log('No results in selectedItemDetails')
    return []
  }
  const workshopId = (props.workshop as any).workshop_id || (props.workshop as any).id
  console.log('Filtering results for workshop:', workshopId)
  console.log('All results:', selectedItemDetails.value.results)
  
  // Filter results for this workshop and sort by created_at desc
  const filtered = selectedItemDetails.value.results
    .filter((r: any) => {
      console.log('Checking result:', r.workshop_id, 'against', workshopId)
      return r.workshop_id === workshopId
    })
    .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  
  console.log('Filtered results:', filtered)
  return filtered
})

// 最新结果（默认展示）
const latestResult = computed(() => {
  const result = existingResults.value[0] || null
  console.log('Latest result:', result)
  return result
})

// 历史版本（除了最新的）
const historicalResults = computed(() => existingResults.value.slice(1))

// 当前任务状态
const currentTaskStatus = computed(() => {
  if (!activeTaskId.value) return null
  return workshopsStore.tasks[activeTaskId.value]?.status || 'pending'
})

// 是否正在生成中
const isGenerating = computed(() => {
  return activeTaskId.value && (currentTaskStatus.value === 'pending' || currentTaskStatus.value === 'in_progress')
})

// Simple markdown-like rendering
const renderMarkdown = (text: string) => {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold mt-6 mb-3">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>')
    .replace(/^- (.*$)/gim, '<li class="ml-4">$1</li>')
    .replace(/\n/g, '<br>')
}

const viewResultDetail = (result: any) => {
  selectedResult.value = result
  resultDetailDialogOpen.value = true
}

const saveChanges = async () => {
  saving.value = true
  try {
    await workshopsStore.updateWorkshop((props.workshop as any).workshop_id || (props.workshop as any).id, {
      name: name.value,
      // backend unified fields only
      // @ts-ignore
      default_prompt: systemPrompt.value || userPrompt.value || '',
    } as any)
  } finally {
    saving.value = false
  }
}

const execute = async () => {
  if (selectedItemId.value == null) return
  running.value = true
  try {
    const taskId = await workshopsStore.executeWorkshop(
      (props.workshop as any).workshop_id || (props.workshop as any).id,
      selectedItemId.value,
      {
        // Only send prompt if provided; backend also supports llm_model
        prompt: userPrompt.value || systemPrompt.value || undefined,
      }
    )
    if (taskId) {
      activeTaskId.value = taskId
      workshopsStore.subscribeToTask(taskId)
    }
  } finally {
    running.value = false
  }
}

// Watch for selected item changes and fetch details
watch(selectedItemId, async (newId, oldId) => {
  // 切换收藏项时清空当前任务状态
  activeTaskId.value = null
  
  // Update URL query parameter
  if (newId !== oldId) {
    const query = newId ? { item: newId.toString() } : {}
    router.replace({ query })
  }
  
  if (newId) {
    try {
      selectedItemDetails.value = await api.get(`/collections/${newId}`)
    } catch (error) {
      console.error('Failed to fetch item details:', error)
    }
  } else {
    selectedItemDetails.value = null
  }
})

// Watch for URL query changes (e.g., from browser back/forward)
watch(
  () => route.query.item,
  (itemQuery) => {
    const itemId = itemQuery ? parseInt(itemQuery as string) : null
    if (itemId !== selectedItemId.value) {
      selectedItemId.value = itemId
    }
  }
)

// 监听任务状态，完成后清空 activeTaskId
watch(
  () => activeTaskId.value ? workshopsStore.tasks[activeTaskId.value]?.status : null,
  (status) => {
    if (status === 'success' || status === 'failure') {
      // 任务完成，延迟清空以便用户看到最终状态
      setTimeout(() => {
        activeTaskId.value = null
        // 刷新详情以获取新生成的结果
        if (selectedItemId.value) {
          api.get(`/collections/${selectedItemId.value}`).then(data => {
            selectedItemDetails.value = data
          })
        }
      }, 1000)
    }
  }
)

onMounted(async () => {
  if (!collectionsStore.items.length) {
    await collectionsStore.fetchCollections()
  }
  
  // If URL has item query, load its details immediately
  if (selectedItemId.value) {
    try {
      selectedItemDetails.value = await api.get(`/collections/${selectedItemId.value}`)
      console.log('Loaded item from URL:', selectedItemDetails.value)
      console.log('Existing results:', existingResults.value)
    } catch (error) {
      console.error('Failed to load item from URL:', error)
    }
  }
})
</script>

<template>
  <div class="h-full flex flex-col">
    <header class="p-4 border-b border-border bg-muted/50 flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-tight">{{ name }}</h2>
      <Dialog v-model:open="promptDialogOpen">
        <DialogTrigger as-child>
          <Button size="sm" variant="outline">
            <Settings class="w-4 h-4 mr-2" />
            提示词配置
          </Button>
        </DialogTrigger>
        <DialogContent class="max-w-2xl">
          <DialogHeader>
            <DialogTitle>提示词配置</DialogTitle>
          </DialogHeader>
          <div class="space-y-4 py-4">
            <div class="space-y-2">
              <label class="text-sm font-medium">系统提示词</label>
              <textarea v-model="systemPrompt" rows="6" class="w-full border rounded-md p-3 text-sm resize-none"></textarea>
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium">用户提示模板</label>
              <textarea v-model="userPrompt" rows="6" class="w-full border rounded-md p-3 text-sm resize-none"></textarea>
            </div>
            <div class="flex justify-end gap-2">
              <Button variant="outline" @click="promptDialogOpen = false">取消</Button>
              <Button @click="saveChanges(); promptDialogOpen = false" :disabled="saving">
                {{ saving ? '保存中...' : '保存' }}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </header>

    <div class="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-px bg-border overflow-hidden">
      <!-- 左侧：源材料选择 -->
      <div class="bg-background flex flex-col h-full">
        <div class="p-4 border-b border-border flex items-center justify-between">
          <h3 class="font-semibold">选择收藏项目</h3>
          <Button size="sm" variant="outline" @click="collectionsStore.fetchCollections()">刷新</Button>
        </div>
        <ScrollArea class="flex-1 p-4">
          <Card
            v-for="item in collectionsStore.items"
            :key="item.id"
            class="mb-2 cursor-pointer hover:bg-muted"
            :class="selectedItemId === item.id ? 'ring-2 ring-primary' : ''"
            @click="selectedItemId = item.id"
          >
            <CardContent class="p-3">
              <p class="text-sm font-medium">{{ item.title }}</p>
              <p class="text-xs text-muted-foreground capitalize">{{ item.platform }} - {{ item.author?.username || '' }}</p>
            </CardContent>
          </Card>
        </ScrollArea>
        <div class="p-4 border-t border-border">
          <Button class="w-full" :disabled="!selectedItemId || running" @click="execute">
            {{ running ? '执行中...' : '执行' }}
          </Button>
        </div>
      </div>

      <!-- 右侧：结果显示（占据更大空间）-->
      <div class="lg:col-span-2 bg-background flex flex-col h-full">
        <div class="p-4 border-b border-border">
          <h3 class="font-semibold">AI 生成结果</h3>
        </div>
        
        <ScrollArea class="flex-1">
          <!-- 当前任务结果（正在生成）-->
          <div v-if="isGenerating" class="border-b p-6 bg-primary/5">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2">
                <Badge class="text-xs">⚡ 正在生成</Badge>
                <Badge variant="outline" class="text-xs">{{ currentTaskStatus }}</Badge>
              </div>
              <span class="text-xs text-muted-foreground font-mono">{{ activeTaskId }}</span>
            </div>
            <div 
              class="prose dark:prose-invert max-w-none" 
              v-html="renderMarkdown(workshopsStore.tasks[activeTaskId!]?.result?.content || '等待结果...')"
            />
          </div>

          <!-- 最新版本（完整展示）-->
          <div v-if="latestResult" class="p-6 border-b">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2">
                <Badge variant="default" class="text-xs">最新版本</Badge>
                <span class="text-xs text-muted-foreground">
                  {{ new Date(latestResult.created_at).toLocaleString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
                </span>
              </div>
              <Button size="sm" variant="ghost" @click="viewResultDetail(latestResult)">
                <Maximize2 class="h-4 w-4 mr-2" />
                全屏查看
              </Button>
            </div>
            <div 
              class="prose dark:prose-invert max-w-none" 
              v-html="renderMarkdown(latestResult.content)"
            />
          </div>

          <!-- 历史版本（折叠）-->
          <Collapsible v-if="historicalResults.length > 0" v-model:open="historyExpanded" class="border-b">
            <CollapsibleTrigger class="w-full p-4 hover:bg-muted/50 transition-colors flex items-center justify-between">
              <div class="flex items-center gap-2">
                <History class="h-4 w-4 text-muted-foreground" />
                <span class="text-sm font-medium">历史版本</span>
                <Badge variant="outline" class="text-xs">{{ historicalResults.length }}</Badge>
              </div>
              <ChevronDown 
                class="h-4 w-4 text-muted-foreground transition-transform" 
                :class="{ 'rotate-180': historyExpanded }"
              />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div class="p-4 space-y-3 bg-muted/20">
                <Card 
                  v-for="(result, index) in historicalResults" 
                  :key="result.id" 
                  class="cursor-pointer hover:shadow-md transition-shadow"
                  @click="viewResultDetail(result)"
                >
                  <CardContent class="p-4">
                    <div class="flex items-center justify-between mb-3">
                      <Badge variant="outline" class="text-xs">版本 #{{ historicalResults.length - index }}</Badge>
                      <div class="flex items-center gap-2">
                        <span class="text-xs text-muted-foreground">
                          {{ new Date(result.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
                        </span>
                        <Button size="icon" variant="ghost" class="h-6 w-6">
                          <Maximize2 class="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    <div 
                      class="prose prose-sm dark:prose-invert max-w-none line-clamp-3" 
                      v-html="renderMarkdown(result.content)"
                    />
                  </CardContent>
                </Card>
              </div>
            </CollapsibleContent>
          </Collapsible>

          <!-- 空状态 -->
          <div v-if="!latestResult && !isGenerating" class="flex-1 flex items-center justify-center p-8 min-h-[400px]">
            <p class="text-sm text-muted-foreground text-center">
              {{ selectedItemId ? '该项目暂无结果，点击执行按钮生成。' : '选择一个收藏项目开始。' }}
            </p>
          </div>
        </ScrollArea>
      </div>
    </div>

    <!-- 结果详情弹窗 -->
    <Dialog v-model:open="resultDetailDialogOpen">
      <DialogContent class="max-w-4xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <div class="flex items-center justify-between">
            <DialogTitle>结果详情</DialogTitle>
            <div class="flex items-center gap-2">
              <Badge variant="outline" class="text-xs">
                {{ new Date(selectedResult?.created_at).toLocaleString('zh-CN') }}
              </Badge>
            </div>
          </div>
        </DialogHeader>
        <ScrollArea class="flex-1 -mx-6 px-6 py-4">
          <div 
            class="prose dark:prose-invert max-w-none prose-headings:scroll-mt-20" 
            v-html="renderMarkdown(selectedResult?.content || '')"
          />
        </ScrollArea>
      </DialogContent>
    </Dialog>
  </div>
</template>
