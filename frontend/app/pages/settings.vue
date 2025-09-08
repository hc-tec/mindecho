<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2 } from 'lucide-vue-next'

const settingsStore = useSettingsStore()
const settings = computed(() => settingsStore.settings)
const isLoading = computed(() => settingsStore.loading)

onMounted(() => {
  settingsStore.fetchSettings()
})

const handleUpdate = (key: string, value: any) => {
  settingsStore.updateSettings({ [key]: value })
}
</script>

<template>
  <div class="h-full flex flex-col">
    <header class="p-4 border-b border-border bg-muted/50">
      <h2 class="text-2xl font-bold tracking-tight">设置</h2>
      <p class="text-muted-foreground">管理你的应用配置。</p>
    </header>

    <div class="flex-1 p-4">
      <div v-if="isLoading && !settings" class="flex items-center justify-center h-full">
        <Loader2 class="w-8 h-8 animate-spin text-primary" />
      </div>
      <div v-else-if="settings" class="max-w-2xl mx-auto space-y-6">
        <!-- Appearance Settings -->
        <Card>
          <CardHeader>
            <CardTitle>外观</CardTitle>
            <CardDescription>自定义应用的外观和感觉。</CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <Label for="theme">主题</Label>
              <Select :model-value="settings.theme" @update:model-value="val => handleUpdate('theme', val)">
                <SelectTrigger class="w-[180px]">
                  <SelectValue placeholder="选择主题" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">明亮</SelectItem>
                  <SelectItem value="dark">暗黑</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <!-- AI Settings -->
        <Card>
          <CardHeader>
            <CardTitle>AI 配置</CardTitle>
            <CardDescription>配置 AI 工作坊和模型的行为。</CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <Label for="ai-model">AI 模型</Label>
              <Select :model-value="settings.ai_model" @update:model-value="val => handleUpdate('ai_model', val)">
                <SelectTrigger class="w-[280px]">
                  <SelectValue placeholder="选择模型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gemini-2.5-flash-preview-05-20">gemini-2.5-flash-preview-05-20</SelectItem>
                  <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                  <SelectItem value="claude-3-opus">Claude 3 Opus</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="flex items-center justify-between">
              <Label for="auto-process">自动处理新收藏</Label>
              <Switch id="auto-process" :checked="settings.auto_process" @update:checked="val => handleUpdate('auto_process', val)" />
            </div>
          </CardContent>
        </Card>
        
        <!-- Sync Settings -->
        <Card>
          <CardHeader>
            <CardTitle>同步</CardTitle>
            <CardDescription>管理数据同步选项。</CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <Label for="notifications">启用通知</Label>
              <Switch id="notifications" :checked="settings.notifications_enabled" @update:checked="val => handleUpdate('notifications_enabled', val)" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>
