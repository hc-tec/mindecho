<script setup lang="ts">
import { ref, watchEffect, computed, watch, nextTick, triggerRef } from 'vue'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectGroup, SelectLabel } from '@/components/ui/select'
import { Settings2 } from 'lucide-vue-next'
import { useWorkshopsStore } from '@/stores/workshops'
import { useCollectionsStore } from '@/stores/collections'
import WorkshopPlatformBindings from './WorkshopPlatformBindings.vue'
import AIModelSelector from '@/components/common/AIModelSelector.vue'
import type { Workshop } from '@/types/api'
import { api } from '@/lib/api'

const props = defineProps<{
  open: boolean
  workshop?: Workshop | null
}>()
const emits = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'saved'): void
}>()

const store = useWorkshopsStore()
const collectionsStore = useCollectionsStore()

const isEdit = ref(false)
const name = ref('')
const workshopId = ref('') // slug
const description = ref('')
const defaultPrompt = ref('')
const defaultModel = ref('yuanbao-chat')  // 更新默认值为新的模型ID格式
const executorType = ref('llm_chat')
const executorConfig = ref<Record<string, any> | null>(null)
const executorConfigText = ref('')

// Listening configuration
const listeningEnabled = ref(false)
const platformBindingsDialogOpen = ref(false)
const platformBindingsSummary = ref('未配置')  // 改用 ref 而不是 computed

// Helper: get collection by ID
const getCollectionById = (collectionId: number) => {
  return collectionsStore.platformCollections.find(c => c.id === collectionId)
}

// Helper: 手动计算 platform bindings summary
const updatePlatformBindingsSummary = () => {
  const bindings = executorConfig.value?.platform_bindings || []
  if (!bindings || bindings.length === 0) {
    platformBindingsSummary.value = '未配置'
    return
  }

  const parts: string[] = []

  bindings.forEach((b: any) => {
    const platformIcon = b.platform === 'bilibili' ? '📺' : b.platform === 'xiaohongshu' ? '📕' : '📁'
    const collectionNames = b.collection_ids
      .map((id: number) => getCollectionById(id)?.title)
      .filter((title: string | undefined) => title !== undefined)

    if (collectionNames.length > 0) {
      parts.push(`${platformIcon} ${collectionNames.join('、')}`)
    } else {
      const platformName = b.platform === 'bilibili' ? 'B站' : b.platform === 'xiaohongshu' ? '小红书' : b.platform
      parts.push(`${platformIcon} ${platformName}(${b.collection_ids.length}个)`)
    }
  })

  platformBindingsSummary.value = parts.join(' | ')
  console.log('🔄 platformBindingsSummary 已更新为:', platformBindingsSummary.value)
}

watchEffect(() => {
  if (props.workshop) {
    isEdit.value = true
    name.value = props.workshop.name
    // @ts-ignore backend returns workshop_id
    workshopId.value = (props.workshop as any).workshop_id || ''
    description.value = props.workshop.description || ''
    // map older fields to new defaults if present
    // @ts-ignore
    defaultPrompt.value = (props.workshop as any).default_prompt || props.workshop.system_prompt || ''
    // @ts-ignore
    defaultModel.value = (props.workshop as any).default_model || props.workshop.model || 'gpt-4o-mini'
    // @ts-ignore
    executorType.value = (props.workshop as any).executor_type || (props.workshop as any).type || 'generic'
    // @ts-ignore
    executorConfig.value = (props.workshop as any).executor_config || (props.workshop as any).config || null
    executorConfigText.value = executorConfig.value ? JSON.stringify(executorConfig.value, null, 2) : ''

    // Load listening config
    listeningEnabled.value = executorConfig.value?.listening_enabled || false

    // 手动更新 summary
    updatePlatformBindingsSummary()
  } else {
    isEdit.value = false
    name.value = ''
    workshopId.value = ''
    description.value = ''
    defaultPrompt.value = ''
    defaultModel.value = 'gpt-4o-mini'
    executorType.value = 'generic'
    executorConfig.value = null
    executorConfigText.value = ''
    listeningEnabled.value = false
    platformBindingsSummary.value = '未配置'
  }
})

const saving = ref(false)

const handleSave = async () => {
  saving.value = true
  try {
    // Parse JSON text if user manually edited it
    if (executorConfigText.value.trim()) {
      try {
        executorConfig.value = JSON.parse(executorConfigText.value)
      } catch (e) {
        alert('执行器配置不是有效的 JSON')
        saving.value = false
        return
      }
    }

    // Ensure executor_config exists
    if (!executorConfig.value) {
      executorConfig.value = {}
    }

    // Update listening_enabled
    executorConfig.value.listening_enabled = listeningEnabled.value

    console.log('💾 Saving executor_config:', executorConfig.value)

    if (isEdit.value && props.workshop) {
      await store.updateWorkshop(workshopId.value || (props.workshop as any).workshop_id, {
        name: name.value,
        description: description.value,
        // backend unified fields
        // @ts-ignore
        default_prompt: defaultPrompt.value,
        // @ts-ignore
        default_model: defaultModel.value,
        // @ts-ignore
        executor_type: executorType.value,
        // @ts-ignore
        executor_config: executorConfig.value,
      } as any)
    } else {
      await store.createWorkshop({
        // @ts-ignore
        workshop_id: workshopId.value,
        name: name.value,
        description: description.value,
        // @ts-ignore
        default_prompt: defaultPrompt.value,
        // @ts-ignore
        default_model: defaultModel.value,
        // @ts-ignore
        executor_type: executorType.value,
        // @ts-ignore
        executor_config: executorConfig.value,
      } as any)
    }
    emits('saved')
    emits('update:open', false)
  } finally {
    saving.value = false
  }
}

const openPlatformBindings = () => {
  platformBindingsDialogOpen.value = true
}

const onBindingsSaved = async () => {
  if (!workshopId.value) {
    console.warn('❌ No workshop ID')
    return
  }

  console.log('🔄 收藏夹配置保存完成，刷新数据...')
  console.log('   Workshop ID:', workshopId.value)

  try {
    // 1. 先刷新 collections 数据
    console.log('   刷新 collections...')
    await collectionsStore.fetchPlatformCollections()
    console.log('   ✓ Collections 已刷新，总数:', collectionsStore.platformCollections.length)

    // 2. 重新获取最新数据
    const updated = await store.fetchWorkshopBySlug(workshopId.value)

    if (!updated) {
      console.error('❌ 获取更新后的工坊数据失败')
      return
    }

    console.log('✓ 获取到更新后的工坊:', updated)

    const newExecutorConfig = (updated as any).executor_config
    console.log('✓ 新的 executor_config:', newExecutorConfig)
    console.log('✓ 包含 platform_bindings:', newExecutorConfig?.platform_bindings)

    // 关键：强制替换整个对象，确保触发��应式更新
    executorConfig.value = { ...newExecutorConfig }
    executorConfigText.value = JSON.stringify(executorConfig.value, null, 2)
    listeningEnabled.value = executorConfig.value?.listening_enabled || false

    // 强制触发响应式
    triggerRef(executorConfig)
    await nextTick()

    console.log('✅ executorConfig.value 已更新!', executorConfig)
    console.log('   platform_bindings:', executorConfig.value?.platform_bindings)

    // 3. 手动更新 platformBindingsSummary
    updatePlatformBindingsSummary()
    console.log('   ✓ updatePlatformBindingsSummary 已调用')

    // 4. 测试：读取更新后的值
    const testSummary = platformBindingsSummary.value
    console.log('   📊 platformBindingsSummary 最终值:', testSummary)

    if (testSummary === '未配置') {
      console.warn('⚠️  platformBindingsSummary 仍然显示"未配置"')
      console.log('   检查 collections:', collectionsStore.platformCollections.slice(0, 3))
    } else {
      console.log('✅ platformBindingsSummary 已正确更新!')
    }
  } catch (error) {
    console.error('❌ onBindingsSaved 出错:', error)
  }
}

// Load collections when dialog opens
watch(() => props.open, (newVal) => {
  if (newVal) {
    collectionsStore.fetchPlatformCollections()
  }
})
</script>

<template>
  <Dialog :open="open" @update:open="val => emits('update:open', val)">
    <DialogContent class="max-w-2xl">
      <DialogHeader>
        <DialogTitle>{{ isEdit ? '编辑工坊' : '新建工坊' }}</DialogTitle>
      </DialogHeader>

      <div class="space-y-4 max-h-[70vh] overflow-y-auto">
        <div>
          <label class="text-sm font-medium">名称</label>
          <Input v-model="name" placeholder="工坊名称" />
        </div>
        <div>
          <label class="text-sm font-medium">工坊 ID (slug)</label>
          <Input v-model="workshopId" placeholder="如 information-alchemy" :disabled="isEdit" />
        </div>
        <div>
          <label class="text-sm font-medium">描述</label>
          <Textarea v-model="description" rows="3" />
        </div>
        <div>
          <label class="text-sm font-medium">默认提示词</label>
          <Textarea v-model="defaultPrompt" rows="4" placeholder="系统提示词，支持 {source} 变量..." />
        </div>

        <!-- AI模型选择器 -->
        <div class="space-y-2">
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium">AI 模型</label>
            <span class="text-xs text-muted-foreground">
              选择此工坊使用的AI模型进行内容分析
            </span>
          </div>
          <AIModelSelector v-model="defaultModel" />
        </div>

        <div>
          <label class="text-sm font-medium">执行器类型</label>
          <Input v-model="executorType" placeholder="如 llm_chat / generic" />
        </div>

        <!-- Listening Configuration -->
        <Card v-if="isEdit" class="border-primary/20">
          <CardHeader>
            <CardTitle class="text-base flex items-center gap-2">
              <Settings2 class="h-4 w-4" />
              监听配置
            </CardTitle>
            <CardDescription>配置工坊的自动监听与平台绑定</CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <div class="space-y-0.5">
                <Label class="text-sm font-medium">启用监听</Label>
                <p class="text-xs text-muted-foreground">自动监听绑定的收藏夹并触发任务</p>
              </div>
              <Switch v-model="listeningEnabled" />
            </div>

            <div class="space-y-2">
              <Label class="text-sm font-medium">平台绑定</Label>
              <div class="flex items-center gap-2">
                <div class="flex-1 px-3 py-2 border rounded-md bg-muted/30 text-sm">
                  {{ platformBindingsSummary }}
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  @click="openPlatformBindings"
                  :disabled="!workshopId"
                >
                  <Settings2 class="h-4 w-4 mr-1" />
                  配置
                </Button>
              </div>
              <p class="text-xs text-muted-foreground">
                选择要监听的平台和收藏夹，支持多平台多收藏夹绑定
              </p>
            </div>
          </CardContent>
        </Card>

        <details class="border rounded-lg p-3">
          <summary class="cursor-pointer text-sm font-medium mb-2">高级配置 (JSON)</summary>
          <div class="mt-2">
            <Textarea v-model="executorConfigText" rows="6" placeholder='{"ui": {"icon": "Sparkles"}}' class="font-mono text-xs" />
            <p class="text-xs text-muted-foreground mt-1">
              直接编辑 executor_config JSON（包含监听配置）
            </p>
          </div>
        </details>
      </div>

      <div class="flex justify-end gap-2 mt-4">
        <Button variant="ghost" @click="emits('update:open', false)">取消</Button>
        <Button :disabled="saving" @click="handleSave">{{ isEdit ? '保存' : '创建' }}</Button>
      </div>
    </DialogContent>
  </Dialog>

  <!-- Platform Bindings Dialog -->
  <WorkshopPlatformBindings
    v-if="isEdit"
    :open="platformBindingsDialogOpen"
    :workshop-id="workshopId"
    :workshop-name="name"
    @update:open="platformBindingsDialogOpen = $event"
    @saved="onBindingsSaved"
  />
</template>

