<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useWorkshopsStore } from '@/stores/workshops'
import { useCollectionsStore } from '@/stores/collections'
import { useToast } from '@/composables/use-toast'
import type { Collection } from '@/types/api'

const props = defineProps<{
  open: boolean
  workshopId: string
  workshopName: string
}>()

const emits = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'saved'): void
}>()

const workshopsStore = useWorkshopsStore()
const collectionsStore = useCollectionsStore()
const { toast } = useToast()

const loading = ref(false)
const saving = ref(false)

// Platform bindings state
const platformBindings = ref<Array<{ platform: string; collection_ids: number[] }>>([])

// Available platforms
const availablePlatforms = [
  { value: 'bilibili', label: 'B站', icon: '📺' },
  { value: 'xiaohongshu', label: '小红书', icon: '📕' }
]

// Computed: Collections grouped by platform
const collectionsByPlatform = computed(() => {
  const grouped: Record<string, Collection[]> = {}

  for (const collection of collectionsStore.platformCollections) {
    if (!grouped[collection.platform]) {
      grouped[collection.platform] = []
    }
    grouped[collection.platform].push(collection)
  }

  return grouped
})

// Check if a collection is selected
const isCollectionSelected = (platform: string, collectionId: number) => {
  const binding = platformBindings.value.find(b => b.platform === platform)
  return binding?.collection_ids.includes(collectionId) || false
}

// Toggle collection selection
const toggleCollection = (platform: string, collectionId: number) => {
  const binding = platformBindings.value.find(b => b.platform === platform)

  if (!binding) {
    // Create new binding for this platform
    platformBindings.value = [
      ...platformBindings.value,
      { platform, collection_ids: [collectionId] }
    ]
  } else {
    const index = binding.collection_ids.indexOf(collectionId)
    if (index > -1) {
      // Remove collection
      const newCollectionIds = binding.collection_ids.filter(id => id !== collectionId)
      if (newCollectionIds.length === 0) {
        // Remove entire platform binding if no collections left
        platformBindings.value = platformBindings.value.filter(b => b.platform !== platform)
      } else {
        // Update collection_ids immutably
        platformBindings.value = platformBindings.value.map(b =>
          b.platform === platform
            ? { ...b, collection_ids: newCollectionIds }
            : b
        )
      }
    } else {
      // Add collection immutably
      platformBindings.value = platformBindings.value.map(b =>
        b.platform === platform
          ? { ...b, collection_ids: [...b.collection_ids, collectionId] }
          : b
      )
    }
  }
}

// Get selected count for a platform
const getSelectedCount = (platform: string) => {
  const binding = platformBindings.value.find(b => b.platform === platform)
  return binding?.collection_ids.length || 0
}

// Get collection by ID
const getCollectionById = (collectionId: number): Collection | undefined => {
  return collectionsStore.platformCollections.find(c => c.id === collectionId)
}

// Get collection names for a binding
const getBindingCollectionNames = (binding: { platform: string; collection_ids: number[] }): string[] => {
  return binding.collection_ids
    .map(id => getCollectionById(id)?.title)
    .filter((title): title is string => title !== undefined)
}

// Load data when dialog opens
const loadData = async () => {
  loading.value = true
  try {
    // Load current bindings
    const response = await workshopsStore.getPlatformBindings(props.workshopId)
    platformBindings.value = response.platform_bindings || []

    // Load all collections (without platform filter to get all)
    await collectionsStore.fetchPlatformCollections()

    console.log('Loaded collections:', collectionsStore.platformCollections)
    console.log('Current bindings:', platformBindings.value)
  } catch (error) {
    console.error('Failed to load platform bindings:', error)
    toast({
      title: '加载失败',
      description: '无法加载平台绑定配置',
      variant: 'destructive'
    })
  } finally {
    loading.value = false
  }
}

// Watch for dialog open state change
watch(() => props.open, (newVal) => {
  if (newVal && props.workshopId) {
    loadData()
  }
}, { immediate: true })

// Save bindings
const handleSave = async () => {
  saving.value = true

  console.log('💾 开始保存平台绑定...')
  console.log('   Workshop ID:', props.workshopId)
  console.log('   platformBindings.value:', JSON.stringify(platformBindings.value, null, 2))

  try {
    const result = await workshopsStore.updatePlatformBindings(props.workshopId, platformBindings.value)
    console.log('✅ 保存成功！返回结果:', result)

    toast({
      title: '保存成功',
      description: '平台绑定已更新'
    })

    console.log('🔔 触发 saved 事件')
    emits('saved')
    emits('update:open', false)
  } catch (error) {
    console.error('Failed to save platform bindings:', error)
    toast({
      title: '保存失败',
      description: '无法保存平台绑定配置',
      variant: 'destructive'
    })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="val => emits('update:open', val)">
    <DialogContent class="max-w-4xl max-h-[80vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>平台监听绑定 - {{ workshopName }}</DialogTitle>
        <p class="text-sm text-muted-foreground mt-2">
          选择要监听的平台和收藏夹。当这些收藏夹有新内容时，将自动触发此工坊进行处理。
        </p>
      </DialogHeader>

      <div v-if="loading" class="flex items-center justify-center py-8">
        <div class="text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p class="text-sm text-muted-foreground mt-2">加载中...</p>
        </div>
      </div>

      <div v-else class="space-y-6">
        <!-- Summary -->
        <Card v-if="platformBindings.length > 0">
          <CardHeader>
            <CardTitle class="text-sm">当前绑定</CardTitle>
            <CardDescription class="text-xs">已选中的收藏夹列表</CardDescription>
          </CardHeader>
          <CardContent class="space-y-3">
            <div
              v-for="binding in platformBindings"
              :key="binding.platform"
              class="flex items-start gap-2"
            >
              <span class="text-xl mt-0.5 shrink-0">{{ availablePlatforms.find(p => p.value === binding.platform)?.icon }}</span>
              <div class="flex-1 min-w-0">
                <div class="flex flex-wrap gap-1.5 items-center">
                  <template v-if="getBindingCollectionNames(binding).length > 0">
                    <span
                      v-for="(collectionName, idx) in getBindingCollectionNames(binding)"
                      :key="idx"
                      class="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary rounded text-xs font-medium"
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
          </CardContent>
        </Card>

        <!-- Platform Sections -->
        <div
          v-for="platform in availablePlatforms"
          :key="platform.value"
          class="space-y-3"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-2xl">{{ platform.icon }}</span>
              <h3 class="text-lg font-semibold">{{ platform.label }}</h3>
              <span class="text-sm text-muted-foreground">
                ({{ getSelectedCount(platform.value) }} 已选择)
              </span>
            </div>
          </div>

          <!-- Collections List -->
          <div v-if="collectionsByPlatform[platform.value]?.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div
              v-for="collection in collectionsByPlatform[platform.value]"
              :key="collection.id"
              class="flex items-start gap-3 p-3 border rounded-lg hover:bg-accent cursor-pointer transition-colors"
              @click="toggleCollection(platform.value, collection.id)"
            >
              <Checkbox
                :modelValue="isCollectionSelected(platform.value, collection.id)"
                :as-child="false"
              />
              <div class="flex-1 min-w-0">
                <Label class="cursor-pointer font-medium">{{ collection.title }}</Label>
                <p v-if="collection.description" class="text-xs text-muted-foreground mt-1 line-clamp-2">
                  {{ collection.description }}
                </p>
                <div class="flex items-center gap-2 mt-1">
                  <span class="text-xs text-muted-foreground">{{ collection.item_count }} 条内容</span>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="text-sm text-muted-foreground p-4 border rounded-lg bg-muted/30">
            <p>该平台暂无同步的收藏夹。</p>
            <p class="mt-1">请先在「同步」页面同步该平台的收藏夹列表。</p>
          </div>
        </div>
      </div>

      <DialogFooter class="mt-6">
        <Button variant="ghost" @click="emits('update:open', false)">取消</Button>
        <Button :disabled="saving || loading" @click="handleSave">
          {{ saving ? '保存中...' : '保存绑定' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
