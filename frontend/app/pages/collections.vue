<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCollectionsStore } from '@/stores/collections'
import { useWorkshopsStore } from '@/stores/workshops'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Pagination, PaginationContent, PaginationEllipsis, PaginationFirst, PaginationLast, PaginationItem, PaginationNext, PaginationPrev } from '@/components/ui/pagination'
import { Badge } from '@/components/ui/badge'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { format } from 'date-fns'
import { Loader2, Search } from 'lucide-vue-next'
import type { FavoriteItem } from '@/types/api'

const router = useRouter()
const store = useCollectionsStore()
const workshopsStore = useWorkshopsStore()

onMounted(async () => {
  // 先加载工作坊列表（用于智能路由）
  if (workshopsStore.workshops.length === 0) {
    await workshopsStore.fetchWorkshops()
  }
  await store.fetchCollections()
  await store.fetchTags()
})

const totalPages = computed(() => Math.ceil(store.total / store.itemsPerPage))

const formatDate = (dateString: string) => {
  return dateString ? format(new Date(dateString), 'yyyy-MM-dd HH:mm') : 'N/A'
}

/**
 * 智能跳转到工作坊
 * 根据item所属的collection查找绑定的工作坊
 */
const navigateToWorkshop = (item: FavoriteItem) => {
  let workshopId = 'summary-01' // 默认工作坊

  // 如果item有collection信息，尝试查找绑定的工作坊
  if (item.collection?.id && item.platform) {
    const boundWorkshop = workshopsStore.getWorkshopByCollection(
      item.collection.id,
      item.platform
    )

    if (boundWorkshop) {
      workshopId = (boundWorkshop as any).workshop_id
      console.log(`Found bound workshop: ${workshopId} for collection ${item.collection.name}`)
    } else {
      // 如果没有找到绑定的工作坊，使用默认工作坊
      const defaultWorkshop = workshopsStore.getDefaultWorkshop()
      if (defaultWorkshop) {
        workshopId = (defaultWorkshop as any).workshop_id
      }
      console.log(`No bound workshop found, using default: ${workshopId}`)
    }
  }

  router.push(`/workshops/${workshopId}?item=${item.id}`)
}
</script>

<template>
  <div class="h-full flex flex-col">
    <header class="p-4 border-b border-border bg-muted/50">
      <h2 class="text-2xl font-bold tracking-tight">收藏管理</h2>
      <p class="text-muted-foreground">浏览、搜索和管理您的所有收藏。</p>
    </header>

    <div class="flex-1 overflow-y-auto p-8">
      <Card>
        <CardHeader>
          <div class="flex items-center justify-between gap-4">
            <div class="flex items-center gap-2 w-full max-w-sm">
              <div class="relative flex-1">
                <Input v-model="store.searchQuery" placeholder="搜索标题或描述..." @keyup.enter="store.search" />
                <Search class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              </div>
              <Button
                variant="outline"
                size="icon"
                @click="store.resetFilters"
                :disabled="!store.searchQuery && store.selectedTags.length === 0"
                title="重置搜索和筛选"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
                  <path d="M21 3v5h-5"/>
                  <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
                  <path d="M8 16H3v5"/>
                </svg>
              </Button>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="outline">
                  标签: {{ store.selectedTags.length > 0 ? `${store.selectedTags.length} 已选` : '全部' }}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent class="max-h-[400px] overflow-y-auto">
                <DropdownMenuItem
                  v-for="tag in store.tags"
                  :key="tag.id"
                  @click="store.toggleTag(tag.name)"
                  class="cursor-pointer"
                >
                  <span :class="['mr-2', store.selectedTags.includes(tag.name) ? 'font-bold text-primary' : '']">
                    {{ store.selectedTags.includes(tag.name) ? '✓ ' : '' }}{{ tag.name }}
                  </span>
                </DropdownMenuItem>
                <div v-if="store.tags.length === 0" class="px-2 py-6 text-center text-sm text-muted-foreground">
                  暂无标签
                </div>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>标题</TableHead>
                <TableHead>平台</TableHead>
                <TableHead>作者</TableHead>
                <TableHead>标签</TableHead>
                <TableHead>收藏于 (最新在前)</TableHead>
                <TableHead>状态</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <template v-if="store.loading">
                <TableRow v-for="i in 5" :key="i">
                  <TableCell colspan="6" class="p-0"><div class="h-12 skeleton" /></TableCell>
                </TableRow>
              </template>
              <template v-else-if="store.items.length > 0">
                <TableRow
                  v-for="item in store.items"
                  :key="item.id"
                  class="cursor-pointer hover:bg-muted/50"
                  @click="navigateToWorkshop(item)"
                >
                  <TableCell class="font-medium">{{ item.title }}</TableCell>
                  <TableCell class="capitalize">{{ item.platform }}</TableCell>
                  <TableCell>{{ item.author?.username || 'N/A' }}</TableCell>
                  <TableCell>
                    <Badge v-for="tag in item.tags" :key="tag.id" variant="secondary" class="mr-1">{{ tag.name }}</Badge>
                  </TableCell>
                  <TableCell>{{ formatDate(item.favorited_at) }}</TableCell>
                  <TableCell>
                    <Badge :variant="item.status === 'processed' ? 'default' : 'outline'">{{ item.status }}</Badge>
                  </TableCell>
                </TableRow>
              </template>
              <template v-else>
                <TableRow>
                  <TableCell colspan="6" class="text-center h-24">无结果。</TableCell>
                </TableRow>
              </template>
            </TableBody>
          </Table>
        </CardContent>
        <CardFooter>
          <Pagination v-if="totalPages > 1" :total="store.total" :page="store.currentPage" @update:page="store.setPage" :items-per-page="store.itemsPerPage" show-edges class="mx-auto">
            <PaginationFirst />
            <PaginationPrev />
            <PaginationContent v-slot="{ items }">
              <template v-for="(item, index) in items" :key="index">
                <PaginationItem v-if="item.type === 'page'" :value="item.value" :is-active="item.value === store.currentPage" as-child>
                  <Button class="w-10 h-10 p-0">
                    {{ item.value }}
                  </Button>
                </PaginationItem>
                <PaginationEllipsis v-else :index="index" />
              </template>
            </PaginationContent>
            <PaginationNext />
            <PaginationLast />
          </Pagination>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>
