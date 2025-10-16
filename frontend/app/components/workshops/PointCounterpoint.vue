<script setup lang="ts">
import { ref, computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Zap } from 'lucide-vue-next'
import { useWorkshopsStore } from '@/stores/workshops'
import type { Workshop } from '@/types/api'

const props = defineProps<{
  workshop: Workshop
}>()

// Store and State Management
const workshopsStore = useWorkshopsStore()
const coreArgumentText = ref('')
const taskId = ref<string | null>(null)

const isLoading = computed(() => workshopsStore.loading)
const taskStatus = computed(() => {
    if (!taskId.value) return 'idle'
    return workshopsStore.tasks[taskId.value]?.status || 'pending'
})
const counterpoints = computed(() => {
    if (!taskId.value) return []
    const task = workshopsStore.tasks[taskId.value]
    // TODO: Adapt this based on the actual structure of task.result
    try {
        if (task?.result?.content) {
            const parsedResult = JSON.parse(task.result.content)
            return parsedResult.counterpoints || []
        }
    } catch (e) {
        console.error("Failed to parse counterpoints:", e)
    }
    return []
})

const handleExecute = async () => {
    if (!coreArgumentText.value.trim()) return
    const currentId = (props.workshop as any).workshop_id || (props.workshop as any).id
    if (!currentId) return
    const newTaskId = await workshopsStore.executeWorkshop(
        currentId,
        undefined,
        { prompt: coreArgumentText.value }
    )
    if (newTaskId) {
        taskId.value = newTaskId
        workshopsStore.subscribeToTask(newTaskId)
    }
}
</script>

<template>
  <div class="fixed inset-0 left-0 md:left-64 flex flex-col bg-background">
    <header class="p-4 border-b border-border bg-muted/50 shrink-0">
      <h2 class="text-2xl font-bold tracking-tight">{{ workshop.name }}</h2>
      <p class="text-muted-foreground">{{ workshop.description }}</p>
    </header>

    <div class="flex-1 grid grid-cols-1 md:grid-cols-3 gap-px bg-border min-h-0 overflow-hidden">
      <!-- Left Column: Core Argument Input -->
      <div class="bg-background flex flex-col h-full">
        <div class="p-4 border-b border-border"><h3 class="font-semibold text-lg">核心论点</h3></div>
        <div class="flex-1 p-4 space-y-4">
            <Card>
                <CardHeader><CardTitle class="text-base">输入一个您想辩论的核心论点</CardTitle></CardHeader>
                <CardContent>
                    <Textarea
                        v-model="coreArgumentText"
                        placeholder="例如：人工智能将最终取代所有人类工作..."
                        class="mb-4"
                        rows="5"
                    />
                    <Button @click="handleExecute" :disabled="isLoading || !coreArgumentText.trim()" class="w-full">
                        <Zap class="w-4 h-4 mr-2" />
                        {{ isLoading ? `[${taskStatus}] 生成中...` : '生成对撞观点' }}
                    </Button>
                </CardContent>
            </Card>
        </div>
      </div>

      <!-- Right Column: AI-Generated Counterarguments -->
      <div class="md:col-span-2 bg-background flex flex-col h-full">
        <div class="p-4 border-b border-border">
          <h3 class="font-semibold text-lg">AI 生成的反驳视角</h3>
          <p class="text-sm text-muted-foreground line-clamp-1" v-if="coreArgumentText">针对: "{{ coreArgumentText }}"</p>
        </div>
        <div class="flex-1 overflow-y-auto p-4 space-y-4">
          <div v-if="isLoading && counterpoints.length === 0" class="text-center text-muted-foreground p-8">
            <p>AI 正在思考, 请稍候...</p>
          </div>
          <div v-else-if="counterpoints.length > 0">
            <Card v-for="(counter, index) in counterpoints" :key="index" class="bg-muted/50">
              <CardContent class="p-4">
                <p class="text-sm">{{ counter.text }}</p>
              </CardContent>
            </Card>
          </div>
          <div v-else class="text-center text-muted-foreground p-8">
            <p>请输入一个核心论点以开始。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
