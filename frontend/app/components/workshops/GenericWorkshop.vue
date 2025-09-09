<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useWorkshopsStore } from '@/stores/workshops'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useCollectionsStore } from '@/stores/collections'
import type { Workshop } from '@/types/api'

const props = defineProps<{ workshop: Workshop }>()

const workshopsStore = useWorkshopsStore()
const collectionsStore = useCollectionsStore()

// local editable copies
const name = ref(props.workshop.name)
const systemPrompt = ref(props.workshop.system_prompt)
const userPrompt = ref(props.workshop.user_prompt_template)

const saving = ref(false)
const running = ref(false)
const selectedItemId = ref<number | null>(null)
const activeTaskId = ref<string | null>(null)

const saveChanges = async () => {
  saving.value = true
  try {
    await workshopsStore.updateWorkshop((props.workshop as any).workshop_id || props.workshop.id, {
      name: name.value,
      // map to backend fields if supported in your schema; keeping for compatibility
      system_prompt: systemPrompt.value,
      user_prompt_template: userPrompt.value,
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
      (props.workshop as any).workshop_id || props.workshop.id,
      selectedItemId.value,
      {
        system_prompt: systemPrompt.value,
        user_prompt_template: userPrompt.value,
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

onMounted(() => {
  if (!collectionsStore.items.length) {
    collectionsStore.fetchCollections()
  }
})
</script>

<template>
  <div class="h-full flex flex-col">
    <header class="p-4 border-b border-border bg-muted/50 flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-tight">{{ name }}</h2>
      <Button size="sm" @click="saveChanges" :disabled="saving">
        保存
      </Button>
    </header>

    <div class="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-px bg-border overflow-hidden">
      <!-- 左侧：提示词配置-->
      <div class="bg-background p-4 space-y-4">
        <h3 class="font-semibold">提示词配置</h3>
        <div class="space-y-2">
          <label class="text-sm font-medium">系统提示词</label>
          <textarea v-model="systemPrompt" rows="4" class="w-full border rounded-md p-2 text-sm"></textarea>
        </div>
        <div class="space-y-2">
          <label class="text-sm font-medium">用户提示模板</label>
          <textarea v-model="userPrompt" rows="4" class="w-full border rounded-md p-2 text-sm"></textarea>
        </div>
      </div>

      <!-- 中间：源材料选择 -->
      <div class="lg:col-span-2 bg-background flex flex-col h-full">
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
              <p class="text-xs text-muted-foreground capitalize">{{ item.platform }} - {{ item.author_name }}</p>
            </CardContent>
          </Card>
        </ScrollArea>
        <div class="p-4 border-t border-border">
          <Button class="w-full" :disabled="!selectedItemId || running" @click="execute">
            {{ running ? '执行中...' : '执行' }}
          </Button>
        </div>
      </div>

      <!-- 右侧：结果输出占位 -->
      <div class="bg-background p-4">
        <h3 class="font-semibold mb-2">任务结果</h3>
        <div v-if="activeTaskId">
          <p class="text-xs text-muted-foreground mb-2">Task: {{ activeTaskId }}</p>
          <div class="prose dark:prose-invert text-sm whitespace-pre-wrap">
            {{ workshopsStore.tasks[activeTaskId]?.result?.content || '等待结果...' }}
          </div>
        </div>
        <p v-else class="text-sm text-muted-foreground">执行任务后将在此显示结果。</p>
      </div>
    </div>
  </div>
</template>
