<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectGroup, SelectLabel } from '@/components/ui/select'
import { api } from '@/lib/api'

/**
 * 可复用的AI模型选择器组件
 *
 * 功能：
 * - 从后端API动态加载可用模型列表
 * - 按提供商分组展示（腾讯、Google、OpenAI等）
 * - 显示模型详细信息（描述、上下文长度、特性标签）
 * - 支持v-model双向绑定
 *
 * 使用示例：
 * <AIModelSelector v-model="selectedModel" class="w-[320px]" />
 */

interface AIModelInfo {
  id: string
  name: string
  provider: string
  description: string
  requires_browser: boolean
  supports_streaming: boolean
  max_tokens: number
  is_default: boolean
}

// Props定义
interface Props {
  modelValue: string  // v-model绑定的模型ID
  disabled?: boolean  // 是否禁用选择器
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false
})

// Emits定义
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

// 状态管理
const availableModels = ref<AIModelInfo[]>([])
const loadingModels = ref(false)

// 提供商显示名称映射（中文本地化）
const providerNames: Record<string, string> = {
  yuanbao: '腾讯',
  google: 'Google',
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  deepseek: 'DeepSeek'
}

// 提供商显示顺序（按流行度/重要性排序）
const providerOrder = ['yuanbao', 'google', 'openai', 'anthropic', 'deepseek']

// 计算当前选中模型的显示名称
const selectedModelName = computed(() => {
  const model = availableModels.value.find(m => m.id === props.modelValue)
  return model?.name || props.modelValue
})

// 从后端API获取可用模型列表
const fetchAvailableModels = async () => {
  try {
    loadingModels.value = true
    const models = await api.get<AIModelInfo[]>('/settings/ai-models')
    availableModels.value = models
  } catch (error) {
    console.error('Failed to fetch AI models:', error)
    // 如果API失败，使用默认模型作为fallback（确保UI可用）
    availableModels.value = [
      {
        id: 'yuanbao-chat',
        name: '元宝 (豆包)',
        provider: 'yuanbao',
        description: '腾讯的AI助手',
        requires_browser: true,
        supports_streaming: true,
        max_tokens: 4096,
        is_default: true
      }
    ]
  } finally {
    loadingModels.value = false
  }
}

// 处理模型选择变化
const handleModelChange = (newModelId: string) => {
  emit('update:modelValue', newModelId)
}

// 组件挂载时加载模型列表
onMounted(() => {
  fetchAvailableModels()
})
</script>

<template>
  <Select
    :model-value="modelValue"
    @update:model-value="handleModelChange"
    :disabled="disabled || loadingModels"
  >
    <SelectTrigger>
      <SelectValue placeholder="选择模型">
        <span v-if="loadingModels">加载模型列表...</span>
        <template v-else>
          {{ selectedModelName }}
        </template>
      </SelectValue>
    </SelectTrigger>

    <SelectContent class="max-h-[400px]">
      <!-- 按提供商分组显示模型 -->
      <template v-for="provider in providerOrder" :key="provider">
        <!-- 只显示有模型的提供商 -->
        <SelectGroup v-if="availableModels.some(m => m.provider === provider)">
          <SelectLabel class="px-2 py-2 font-semibold text-sm capitalize">
            {{ providerNames[provider] || provider }}
          </SelectLabel>

          <!-- 该提供商下的所有模型 -->
          <SelectItem
            v-for="model in availableModels.filter(m => m.provider === provider)"
            :key="model.id"
            :value="model.id"
          >
            <div class="flex flex-col gap-0.5 py-1">
              <!-- 模型名称和标签 -->
              <div class="flex items-center gap-2">
                <span class="font-medium">{{ model.name }}</span>

                <!-- 默认模型标签 -->
                <span
                  v-if="model.is_default"
                  class="text-xs px-1.5 py-0.5 bg-primary/10 text-primary rounded"
                >
                  默认
                </span>

                <!-- 需要浏览器标签（警告色） -->
                <span
                  v-if="model.requires_browser"
                  class="text-xs px-1.5 py-0.5 bg-amber-500/10 text-amber-600 dark:text-amber-400 rounded"
                >
                  需要浏览器
                </span>
              </div>

              <!-- 模型描述 -->
              <span class="text-xs text-muted-foreground">
                {{ model.description }}
              </span>

              <!-- 上下文窗口大小 -->
              <span class="text-xs text-muted-foreground">
                上下文: {{ (model.max_tokens / 1000).toFixed(0) }}K tokens
              </span>
            </div>
          </SelectItem>
        </SelectGroup>
      </template>
    </SelectContent>
  </Select>
</template>
