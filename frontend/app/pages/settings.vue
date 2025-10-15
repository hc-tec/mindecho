<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectGroup, SelectLabel } from '@/components/ui/select'
import { Loader2, Video, BookMarked, Settings2 } from 'lucide-vue-next'
import { useWorkshopsStore } from '@/stores/workshops'
import { api } from '@/lib/api'
import { useCollectionsStore } from '@/stores/collections'
import WorkshopPlatformBindings from '@/components/workshops/WorkshopPlatformBindings.vue'
import AIModelSelector from '@/components/common/AIModelSelector.vue'

const settingsStore = useSettingsStore()
const settings = computed(() => settingsStore.settings)
const isLoading = computed(() => settingsStore.loading)
const workshopsStore = useWorkshopsStore()
const workshops = computed(() => workshopsStore.workshops)
const collectionsStore = useCollectionsStore()

interface CollectionItem {
  id: string
  title: string
  platform: 'bilibili' | 'xiaohongshu'
}

const actualCollections = ref<Array<CollectionItem>>([])

// Platform bindings dialog state
const bindingsDialogOpen = ref(false)
const selectedWorkshopId = ref('')
const selectedWorkshopName = ref('')

const openBindingsDialog = (workshopId: string, workshopName: string) => {
  selectedWorkshopId.value = workshopId
  selectedWorkshopName.value = workshopName
  bindingsDialogOpen.value = true
}

const onBindingsSaved = async () => {
  // Refresh workshops to show updated bindings
  await workshopsStore.fetchWorkshops()
}

const fetchActualCollections = async () => {
  try {
    const response = await api.get<{
      total: number;
      items: Array<{
        id: number;
        platform_collection_id: string;
        title: string;
        platform: 'bilibili' | 'xiaohongshu'
      }>
    }>('/sync/collections')
    actualCollections.value = response.items.map(c => ({
      id: String(c.id),  // 使用数据库ID，转为字符串以保持类型一致
      title: c.title,
      platform: c.platform
    }))
  } catch (error) {
    console.error('Failed to fetch collections:', error)
  }
}

onMounted(() => {
  settingsStore.fetchSettings()
  workshopsStore.fetchWorkshops()
  fetchActualCollections()
})

const updateBinding = async (workshopId: string, val: string) => {
  const cid = val && val !== '__auto__' ? Number(val) : undefined
  await api.put(`/workshops/manage/${workshopId}/binding`, { collection_id: cid })
  const wk = await api.get(`/workshops/manage/${workshopId}`)
  const idx = workshops.value.findIndex((w: any) => w.workshop_id === workshopId)
  if (idx >= 0) workshops.value[idx] = wk as any
}

const handleUpdate = (key: string, value: any) => {
  settingsStore.updateSettings({ [key]: value })
}

// Helper function to get collection by ID
const getCollectionById = (id: string | undefined): CollectionItem | undefined => {
  if (!id) return undefined
  return actualCollections.value.find(c => c.id === id)
}

// Helper function to get collection by numeric ID
const getCollectionByNumericId = (id: number): CollectionItem | undefined => {
  return actualCollections.value.find(c => Number(c.id) === id)
}

// Get collection names for a binding
const getBindingCollectionNames = (binding: any): string[] => {
  if (!binding || !binding.collection_ids || binding.collection_ids.length === 0) {
    return []
  }
  return binding.collection_ids
    .map((id: number) => getCollectionByNumericId(id)?.title)
    .filter((title: string | undefined) => title !== undefined)
}

// Group collections by platform
const collectionsByPlatform = computed(() => {
  const grouped: Record<string, CollectionItem[]> = {
    bilibili: [],
    xiaohongshu: []
  }

  actualCollections.value.forEach(col => {
    if (grouped[col.platform]) {
      grouped[col.platform].push(col)
    }
  })

  return grouped
})

// Platform display names
const platformNames: Record<string, string> = {
  bilibili: '哔哩哔哩',
  xiaohongshu: '小红书'
}

// Platform configurations (icon, color)
const platformConfig: Record<string, { icon: any; colorClass: string; bgClass: string; borderClass: string }> = {
  bilibili: {
    icon: Video,
    colorClass: 'text-[#00A1D6]',
    bgClass: 'bg-[#00A1D6]/10',
    borderClass: 'border-l-[#00A1D6]'
  },
  xiaohongshu: {
    icon: BookMarked,
    colorClass: 'text-[#FF2442]',
    bgClass: 'bg-[#FF2442]/10',
    borderClass: 'border-l-[#FF2442]'
  }
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
              <Select :model-value="settings.theme" @update:model-value="(val: any) => handleUpdate('theme', val)">
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
              <div class="flex flex-col gap-1">
                <Label for="ai-model">AI 模型</Label>
                <span class="text-xs text-muted-foreground">
                  选择用于内容分析的AI模型
                </span>
              </div>
              <AIModelSelector
                :model-value="settings.ai_model"
                @update:model-value="(val: any) => handleUpdate('ai_model', val)"
                class="w-[320px]"
              />
            </div>
            <div class="flex items-center justify-between">
              <Label for="auto-process">自动处理新收藏</Label>
              <Switch :model-value="settings.auto_process" @update:modelValue="(val: any) => handleUpdate('auto_process', val)" />
            </div>
            <div class="flex flex-col gap-2 pt-2 border-t">
              <div class="flex items-center justify-between">
                <div class="flex flex-col gap-1">
                  <Label for="first-sync-threshold">首次同步阈值</Label>
                  <span class="text-xs text-muted-foreground">
                    新增内容超过此数量时，跳过 AI 处理以避免系统过载
                  </span>
                </div>
                <input
                  id="first-sync-threshold"
                  type="number"
                  min="1"
                  :value="settings.first_sync_threshold"
                  @input="(e: any) => handleUpdate('first_sync_threshold', Number(e.target.value))"
                  class="w-24 px-3 py-2 border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
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
              <Switch :model-value="settings.notifications_enabled" @update:modelValue="(val: any) => handleUpdate('notifications_enabled', val)" />
            </div>
          </CardContent>
        </Card>

        <!-- Listening Management -->
        <Card>
          <CardHeader>
            <CardTitle>监听管理</CardTitle>
            <CardDescription>按收藏夹粒度控制每个工坊的监听与绑定。支持多平台多收藏夹绑定。</CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div v-for="wk in workshops" :key="(wk as any).workshop_id" class="border rounded-md p-3 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <div class="font-medium text-sm">{{ wk.name }}</div>
                  <div class="text-xs text-muted-foreground">ID: {{ (wk as any).workshop_id }}</div>
                </div>
                <div class="flex items-center gap-2 select-none">
                  <span class="text-xs text-muted-foreground">监听</span>
                  <Switch :model-value="(wk as any).executor_config?.listening_enabled === true"
                    @update:modelValue="(val: boolean) => workshopsStore.toggleListening((wk as any).workshop_id, Boolean(val), (wk as any).name)" />
                </div>
              </div>

              <!-- Platform Bindings Summary -->
              <div v-if="(wk as any).executor_config?.platform_bindings?.length > 0" class="space-y-2.5">
                <div
                  v-for="binding in (wk as any).executor_config.platform_bindings"
                  :key="binding.platform"
                  class="flex items-start gap-2"
                >
                  <component :is="platformConfig[binding.platform]?.icon || Video" :class="['h-4 w-4 mt-0.5 shrink-0', platformConfig[binding.platform]?.colorClass]" />
                  <div class="flex-1 min-w-0">
                    <div class="flex flex-wrap gap-1.5 items-center">
                      <template v-if="getBindingCollectionNames(binding).length > 0">
                        <span
                          v-for="(collectionName, idx) in getBindingCollectionNames(binding)"
                          :key="idx"
                          class="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium"
                          :class="[platformConfig[binding.platform]?.bgClass, platformConfig[binding.platform]?.colorClass]"
                        >
                          {{ collectionName }}
                        </span>
                      </template>
                      <span v-else class="text-xs text-muted-foreground italic">
                        未找到收藏夹 ({{ binding.collection_ids.length }} 个ID)
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Default: Auto-match by title -->
              <div v-else class="flex items-center gap-2 text-xs text-muted-foreground italic">
                <Settings2 class="h-3.5 w-3.5" />
                <span>默认策略：按标题自动匹配收藏夹</span>
              </div>

              <!-- Actions -->
              <div class="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  class="flex-1"
                  @click="openBindingsDialog((wk as any).workshop_id, wk.name)"
                >
                  <Settings2 class="h-4 w-4 mr-2" />
                  {{ (wk as any).executor_config?.platform_bindings?.length > 0 ? '管理平台绑定' : '配置平台绑定' }}
                </Button>
              </div>

              <!-- Legacy Single Binding (Deprecated Notice) -->
              <details v-if="(wk as any).executor_config?.binding_collection_id" class="text-xs">
                <summary class="cursor-pointer text-muted-foreground mb-2">旧版单收藏夹绑定 (已弃用)</summary>
                <div class="flex items-center gap-2 pl-4">
                  <Label class="text-xs text-muted-foreground">绑定收藏夹</Label>
                  <Select :model-value="(((wk as any).executor_config?.binding_collection_id != null ? String((wk as any).executor_config.binding_collection_id) : '__auto__') as any)"
                    @update:model-value="(val: unknown) => updateBinding((wk as any).workshop_id, String(val))">
                    <SelectTrigger class="w-[280px]">
                      <SelectValue placeholder="按标题自动匹配">
                        <template v-if="(wk as any).executor_config?.binding_collection_id">
                          <span v-if="getCollectionById(String((wk as any).executor_config.binding_collection_id))" class="truncate">
                            {{ getCollectionById(String((wk as any).executor_config.binding_collection_id))?.title }}
                          </span>
                        </template>
                        <template v-else>
                          <span class="text-muted-foreground">按标题自动匹配</span>
                        </template>
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent class="max-h-[320px]">
                      <SelectItem value="__auto__">
                        <span class="text-muted-foreground">按标题自动匹配</span>
                      </SelectItem>

                      <template v-for="(platform, key) in collectionsByPlatform" :key="key">
                        <SelectGroup v-if="platform.length > 0">
                          <SelectLabel :class="['px-2 py-2.5 mt-1 mb-1 rounded-sm flex items-center gap-2 border-l-4', platformConfig[key].bgClass, platformConfig[key].borderClass]">
                            <component :is="platformConfig[key].icon" :class="['h-4 w-4', platformConfig[key].colorClass]" />
                            <span :class="['text-sm font-bold', platformConfig[key].colorClass]">
                              {{ platformNames[key] }}
                            </span>
                          </SelectLabel>
                          <SelectItem v-for="col in platform" :key="col.id" :value="col.id">
                            {{ col.title }}
                          </SelectItem>
                        </SelectGroup>
                      </template>
                    </SelectContent>
                  </Select>
                </div>
              </details>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- Platform Bindings Dialog -->
    <WorkshopPlatformBindings
      :open="bindingsDialogOpen"
      :workshop-id="selectedWorkshopId"
      :workshop-name="selectedWorkshopName"
      @update:open="bindingsDialogOpen = $event"
      @saved="onBindingsSaved"
    />
  </div>
</template>
