<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useCollectionsStore } from '@/stores/collections'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Trash2, Inbox, Loader2 } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { BilibiliImage } from '@/components/ui/bilibili-image'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

const collectionsStore = useCollectionsStore()
const inboxItems = computed(() => collectionsStore.inboxItems)
const isLoading = computed(() => collectionsStore.loading)

onMounted(() => {
  collectionsStore.fetchInbox()
})

const selectedItems = ref<number[]>([])

const toggleSelectAll = (checked: boolean) => {
  if (checked) {
    selectedItems.value = inboxItems.value.map(item => item.id)
  } else {
    selectedItems.value = []
  }
}

const formatRelativeTime = (dateString: string) => {
  if (!dateString) return 'unknown time'
  return formatDistanceToNow(new Date(dateString), { addSuffix: true, locale: zhCN })
}

const handleDelete = () => {
  collectionsStore.deleteItems(selectedItems.value)
  selectedItems.value = []
}

const toggleItem = (itemId: number) => {
  if (selectedItems.value.includes(itemId)) {
    selectedItems.value = selectedItems.value.filter(id => id !== itemId)
  } else {
    selectedItems.value = [...selectedItems.value, itemId]
  }
}
</script>

<template>
  <div class="h-full flex flex-col">
    <header class="p-4 border-b border-border bg-muted/50">
      <h2 class="text-2xl font-bold tracking-tight">收件箱</h2>
      <p class="text-muted-foreground">待处理的收藏和通知。</p>
    </header>

    <div class="flex-1 flex overflow-hidden">
      <div class="flex-1 flex flex-col">
        <div class="p-2 border-b border-border flex items-center gap-2">
          <Checkbox 
            @update:checked="toggleSelectAll" 
            :checked="inboxItems && selectedItems.length === inboxItems.length && inboxItems.length > 0" 
            class="mx-2" 
          />
          <Button variant="outline" size="sm" @click="handleDelete" :disabled="selectedItems.length === 0">
            <Trash2 class="w-4 h-4 mr-2" />
            删除
          </Button>
          <div class="ml-auto text-sm text-muted-foreground">
            已选择 {{ selectedItems.length }} / {{ inboxItems.length }}
          </div>
        </div>

        <div class="flex-1 relative">
          <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
            <Loader2 class="w-8 h-8 animate-spin text-primary" />
          </div>
          <ScrollArea class="h-full">
            <div class="divide-y divide-border">
              <div
                v-for="item in inboxItems"
                :key="item.id"
                :class="[
                  'flex items-start gap-4 p-4 transition-colors group',
                  selectedItems.includes(item.id) ? 'bg-muted' : 'hover:bg-muted/50',
                ]"
              >
                <div @click="toggleItem(item.id)" class="cursor-pointer mt-1">
                  <Checkbox
                    :modelValue="selectedItems.includes(item.id)"
                    @click.prevent.stop
                  />
                </div>
                <BilibiliImage 
                  :src="item.cover_url" 
                  :alt="item.title" 
                  img-class="w-24 h-16 object-cover rounded cursor-pointer shrink-0"
                  @click="$router.push(`/workshops/summary-01?item=${item.id}`)"
                />
                <div class="flex-1 min-w-0 cursor-pointer" @click="$router.push(`/workshops/summary-01?item=${item.id}`)">
                  <div class="flex items-start justify-between gap-2">
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-medium truncate group-hover:text-primary transition-colors">{{ item.title }}</p>
                      <p v-if="item.intro" class="text-xs text-muted-foreground line-clamp-2 mt-1">{{ item.intro }}</p>
                    </div>
                    <span class="text-xs text-muted-foreground shrink-0">{{ formatRelativeTime(item.favorited_at) }}</span>
                  </div>
                  <div class="flex items-center gap-2 mt-2">
                    <Badge variant="outline" class="text-xs capitalize">{{ item.platform }}</Badge>
                    <span v-if="item.author?.username" class="text-xs text-muted-foreground">{{ item.author.username }}</span>
                    <Badge v-if="item.status" :variant="item.status === 'processed' ? 'default' : 'secondary'" class="text-xs">{{ item.status }}</Badge>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="!isLoading && inboxItems.length === 0" class="text-center p-16 text-muted-foreground">
              <Inbox class="w-12 h-12 mx-auto mb-4" />
              <h3 class="font-semibold">收件箱已空</h3>
              <p class="text-sm">没有需要处理的项目。</p>
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  </div>
</template>
