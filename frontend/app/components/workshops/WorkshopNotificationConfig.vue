<script setup lang="ts">
/**
 * 工坊通知配置组件
 *
 * 功能特性：
 * - 启用/禁用通知
 * - 选择处理器（文本格式化、图片渲染）
 * - 选择通知渠道（本地存储、邮件）
 * - 配置处理器参数
 */

import { ref, computed, onMounted, watch } from 'vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Bell, BellOff, Save, RefreshCw } from 'lucide-vue-next'
import {
  getNotificationConfig,
  upsertNotificationConfig,
  type NotificationConfig,
  type ProcessorConfig
} from '@/lib/api'

const props = defineProps<{
  workshopId: string
}>()

const emit = defineEmits<{
  saved: []
}>()

// ============================================================================
// State
// ============================================================================
const loading = ref(false)
const saving = ref(false)
const config = ref<NotificationConfig | null>(null)

// Form data
const enabled = ref(true)
const notifierType = ref<'local_storage' | 'email'>('local_storage')
const textFormat = ref<'markdown' | 'plain' | 'html'>('markdown')
const maxLength = ref<number | null>(null)
const addHeader = ref(true)
const addFooter = ref(false)
const renderImage = ref(false)
const imageStyle = ref('minimal_card')
const imageSize = ref('1080x1920')

// Computed
const processors = computed(() => {
  const result: string[] = ['text_formatter']
  if (renderImage.value) {
    result.push('image_renderer')
  }
  return result
})

const isDirty = computed(() => {
  if (!config.value) return true

  return (
    enabled.value !== config.value.enabled ||
    notifierType.value !== config.value.notifier_type ||
    textFormat.value !== config.value.processor_config.text_format ||
    maxLength.value !== config.value.processor_config.max_length ||
    addHeader.value !== config.value.processor_config.add_header ||
    addFooter.value !== config.value.processor_config.add_footer ||
    renderImage.value !== config.value.processor_config.render_image ||
    imageStyle.value !== config.value.processor_config.image_style ||
    imageSize.value !== config.value.processor_config.image_size
  )
})

// ============================================================================
// Methods
// ============================================================================

/**
 * Load config from server
 */
const loadConfig = async () => {
  loading.value = true
  try {
    const data = await getNotificationConfig(props.workshopId)
    config.value = data

    // Populate form
    enabled.value = data.enabled
    notifierType.value = data.notifier_type
    textFormat.value = data.processor_config.text_format
    maxLength.value = data.processor_config.max_length
    addHeader.value = data.processor_config.add_header
    addFooter.value = data.processor_config.add_footer
    renderImage.value = data.processor_config.render_image
    imageStyle.value = data.processor_config.image_style
    imageSize.value = data.processor_config.image_size
  } catch (error) {
    console.error('Failed to load notification config:', error)
  } finally {
    loading.value = false
  }
}

/**
 * Save config to server
 */
const saveConfig = async () => {
  saving.value = true
  try {
    const processorConfig: ProcessorConfig = {
      text_format: textFormat.value,
      max_length: maxLength.value,
      add_header: addHeader.value,
      add_footer: addFooter.value,
      render_image: renderImage.value,
      image_style: imageStyle.value,
      image_size: imageSize.value,
    }

    const data = await upsertNotificationConfig({
      workshop_id: props.workshopId,
      enabled: enabled.value,
      processors: processors.value,
      notifier_type: notifierType.value,
      processor_config: processorConfig,
      notifier_config: {},
    })

    config.value = data
    emit('saved')
  } catch (error) {
    console.error('Failed to save notification config:', error)
    alert('保存失败：' + (error instanceof Error ? error.message : '未知错误'))
  } finally {
    saving.value = false
  }
}

// ============================================================================
// Lifecycle
// ============================================================================
onMounted(() => {
  loadConfig()
})
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Bell v-if="enabled" class="h-5 w-5 text-primary" />
          <BellOff v-else class="h-5 w-5 text-muted-foreground" />
          <CardTitle>通知配置</CardTitle>
        </div>
        <Badge v-if="enabled" variant="default">已启用</Badge>
        <Badge v-else variant="outline">已禁用</Badge>
      </div>
      <CardDescription>
        配置此工坊完成任务后的通知方式
      </CardDescription>
    </CardHeader>

    <CardContent v-if="!loading" class="space-y-6">
      <!-- 启用开关 -->
      <div class="flex items-center justify-between p-4 border rounded-lg">
        <div class="space-y-0.5">
          <Label class="text-base">启用通知</Label>
          <div class="text-sm text-muted-foreground">
            工坊完成任务后自动发送通知
          </div>
        </div>
        <Switch v-model:checked="enabled" />
      </div>

      <div v-if="enabled" class="space-y-6">
        <!-- 通知渠道 -->
        <div class="space-y-3">
          <Label>通知渠道</Label>
          <Select v-model="notifierType">
            <SelectTrigger>
              <SelectValue placeholder="选择通知渠道" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="local_storage">
                本地存储（保存到文件）
              </SelectItem>
              <SelectItem value="email">
                邮件通知
              </SelectItem>
            </SelectContent>
          </Select>
          <div class="text-xs text-muted-foreground">
            <span v-if="notifierType === 'local_storage'">
              结果将保存到 <code class="bg-muted px-1 py-0.5 rounded">./notifications</code> 目录
            </span>
            <span v-else-if="notifierType === 'email'">
              需要在后端配置 SMTP 环境变量
            </span>
          </div>
        </div>

        <!-- 文本格式 -->
        <div class="space-y-3">
          <Label>文本格式</Label>
          <Select v-model="textFormat">
            <SelectTrigger>
              <SelectValue placeholder="选择文本格式" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="markdown">Markdown</SelectItem>
              <SelectItem value="plain">纯文本</SelectItem>
              <SelectItem value="html">HTML</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <!-- 最大长度 -->
        <div class="space-y-3">
          <Label>最大文本长度</Label>
          <Input
            v-model.number="maxLength"
            type="number"
            placeholder="留空表示不限制"
            min="0"
          />
          <div class="text-xs text-muted-foreground">
            超过长度的内容将被截断（留空表示不限制）
          </div>
        </div>

        <!-- 添加页眉 -->
        <div class="flex items-center justify-between p-4 border rounded-lg">
          <div class="space-y-0.5">
            <Label>添加页眉</Label>
            <div class="text-sm text-muted-foreground">
              在通知内容前添加标题和工坊名称
            </div>
          </div>
          <Switch v-model:checked="addHeader" />
        </div>

        <!-- 添加页脚 -->
        <div class="flex items-center justify-between p-4 border rounded-lg">
          <div class="space-y-0.5">
            <Label>添加页脚</Label>
            <div class="text-sm text-muted-foreground">
              在通知内容后添加 "Generated by MindEcho"
            </div>
          </div>
          <Switch v-model:checked="addFooter" />
        </div>

        <!-- 渲染图片 -->
        <div class="flex items-center justify-between p-4 border rounded-lg">
          <div class="space-y-0.5">
            <Label>渲染图片</Label>
            <div class="text-sm text-muted-foreground">
              通过 RPC 服务将结果渲染为图片
            </div>
          </div>
          <Switch v-model:checked="renderImage" />
        </div>

        <!-- 图片设置（仅在启用图片渲染时显示）-->
        <div v-if="renderImage" class="space-y-4 ml-4 pl-4 border-l-2 border-primary/30">
          <!-- 图片样式 -->
          <div class="space-y-3">
            <Label>图片样式</Label>
            <Input v-model="imageStyle" placeholder="minimal_card" />
          </div>

          <!-- 图片尺寸 -->
          <div class="space-y-3">
            <Label>图片尺寸</Label>
            <Select v-model="imageSize">
              <SelectTrigger>
                <SelectValue placeholder="选择尺寸" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1080x1920">1080x1920 (竖屏)</SelectItem>
                <SelectItem value="1920x1080">1920x1080 (横屏)</SelectItem>
                <SelectItem value="1080x1080">1080x1080 (正方形)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <!-- 当前处理器 -->
        <div class="space-y-3">
          <Label>启用的处理器</Label>
          <div class="flex flex-wrap gap-2">
            <Badge v-for="processor in processors" :key="processor" variant="secondary">
              {{ processor }}
            </Badge>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="flex items-center gap-2 pt-4">
        <Button
          @click="saveConfig"
          :disabled="saving || !isDirty"
          class="flex-1"
        >
          <Save class="h-4 w-4 mr-2" />
          {{ saving ? '保存中...' : '保存配置' }}
        </Button>
        <Button
          variant="outline"
          @click="loadConfig"
          :disabled="loading"
        >
          <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
        </Button>
      </div>

      <!-- 未保存提示 -->
      <div v-if="isDirty && !loading" class="text-xs text-amber-600 dark:text-amber-500">
        ⚠️ 有未保存的更改
      </div>
    </CardContent>

    <CardContent v-else>
      <div class="flex items-center justify-center py-8">
        <RefreshCw class="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    </CardContent>
  </Card>
</template>
