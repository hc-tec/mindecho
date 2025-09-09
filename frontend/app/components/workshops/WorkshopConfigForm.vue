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
const type = ref('generic')
const description = ref('')
const systemPrompt = ref('')
const userPrompt = ref('')
const model = ref('gpt-3.5-turbo')
const temperature = ref(0.7)
const maxTokens = ref(1024)

watchEffect(() => {
  if (props.workshop) {
    isEdit.value = true
    name.value = props.workshop.name
    type.value = props.workshop.type
    description.value = props.workshop.description
    systemPrompt.value = props.workshop.system_prompt
    userPrompt.value = props.workshop.user_prompt_template
    model.value = props.workshop.model || 'gpt-3.5-turbo'
    temperature.value = props.workshop.temperature ?? 0.7
    maxTokens.value = props.workshop.max_tokens ?? 1024
  } else {
    isEdit.value = false
    name.value = ''
    type.value = 'generic'
    description.value = ''
    systemPrompt.value = ''
    userPrompt.value = ''
  }
})

const saving = ref(false)

const handleSave = async () => {
  saving.value = true
  try {
    if (isEdit.value && props.workshop) {
      await store.updateWorkshop(props.workshop.id, {
        name: name.value,
        type: type.value,
        description: description.value,
        system_prompt: systemPrompt.value,
        user_prompt_template: userPrompt.value,
        model: model.value,
        temperature: temperature.value,
        max_tokens: maxTokens.value,
      })
    } else {
      await store.createWorkshop({
        name: name.value,
        type: type.value,
        description: description.value,
        system_prompt: systemPrompt.value,
        user_prompt_template: userPrompt.value,
        model: model.value,
        temperature: temperature.value,
        max_tokens: maxTokens.value,
      })
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
          <label class="text-sm font-medium">类型</label>
          <Input v-model="type" placeholder="generic / information-alchemy" />
        </div>
        <div>
          <label class="text-sm font-medium">描述</label>
          <Textarea v-model="description" rows="3" />
        </div>
        <div>
          <label class="text-sm font-medium">系统提示词</label>
          <Textarea v-model="systemPrompt" rows="4" />
        </div>
        <div>
          <label class="text-sm font-medium">用户提示模板</label>
          <Textarea v-model="userPrompt" rows="4" />
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="text-sm font-medium">模型</label>
            <Input v-model="model" />
          </div>
          <div>
            <label class="text-sm font-medium">温度</label>
            <Input type="number" step="0.1" v-model="temperature" />
          </div>
          <div>
            <label class="text-sm font-medium">Max Tokens</label>
            <Input type="number" v-model="maxTokens" />
          </div>
        </div>
      </div>

      <div class="flex justify-end gap-2 mt-4">
        <Button variant="ghost" @click="emits('update:open', false)">取消</Button>
        <Button :disabled="saving" @click="handleSave">{{ isEdit ? '保存' : '创建' }}</Button>
      </div>
    </DialogContent>
  </Dialog>
</template>
