<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useWorkshopsStore } from '@/stores/workshops'
import type { Workshop } from '@/types/api'

const props = defineProps<{
  open: boolean
  workshop?: Workshop | null
}>()
const emits = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'saved'): void
}>()

const store = useWorkshopsStore()

const isEdit = ref(false)
const name = ref('')
const workshopId = ref('') // slug
const description = ref('')
const defaultPrompt = ref('')
const defaultModel = ref('gpt-4o-mini')
const executorType = ref('generic')
const executorConfig = ref<Record<string, any> | null>(null)

watchEffect(() => {
  if (props.workshop) {
    isEdit.value = true
    name.value = props.workshop.name
    // @ts-ignore backend returns workshop_id
    workshopId.value = (props.workshop as any).workshop_id || ''
    description.value = props.workshop.description
    // map older fields to new defaults if present
    // @ts-ignore
    defaultPrompt.value = (props.workshop as any).default_prompt || props.workshop.system_prompt || ''
    // @ts-ignore
    defaultModel.value = (props.workshop as any).default_model || props.workshop.model || 'gpt-4o-mini'
    // @ts-ignore
    executorType.value = (props.workshop as any).executor_type || (props.workshop as any).type || 'generic'
    // @ts-ignore
    executorConfig.value = (props.workshop as any).executor_config || (props.workshop as any).config || null
  } else {
    isEdit.value = false
    name.value = ''
    workshopId.value = ''
    description.value = ''
    defaultPrompt.value = ''
    defaultModel.value = 'gpt-4o-mini'
    executorType.value = 'generic'
    executorConfig.value = null
  }
})

const saving = ref(false)

const handleSave = async () => {
  saving.value = true
  try {
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
          <Textarea v-model="defaultPrompt" rows="4" />
        </div>
        <div>
          <label class="text-sm font-medium">默认模型</label>
          <Input v-model="defaultModel" placeholder="如 gpt-4o-mini" />
        </div>
        <div>
          <label class="text-sm font-medium">执行器类型</label>
          <Input v-model="executorType" placeholder="如 llm_chat / generic" />
        </div>
        <div>
          <label class="text-sm font-medium">执行器配置 (JSON)</label>
          <Textarea v-model="(executorConfig as any)" rows="4" placeholder='{"ui": {"icon": "Sparkles"}}' />
        </div>
      </div>

      <div class="flex justify-end gap-2 mt-4">
        <Button variant="ghost" @click="emits('update:open', false)">取消</Button>
        <Button :disabled="saving" @click="handleSave">{{ isEdit ? '保存' : '创建' }}</Button>
      </div>
    </DialogContent>
  </Dialog>
</template>

