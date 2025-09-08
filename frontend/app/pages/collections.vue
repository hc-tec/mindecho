<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useCollectionsStore } from '@/stores/collections'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Pagination, PaginationEllipsis, PaginationFirst, PaginationLast, PaginationItem, PaginationNext, PaginationPrev } from '@/components/ui/pagination'
import { Badge } from '@/components/ui/badge'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { format } from 'date-fns'
import { Loader2, Search, ChevronsUpDown, ArrowUp, ArrowDown } from 'lucide-vue-next'

const store = useCollectionsStore()

onMounted(() => {
  store.fetchCollections()
  store.fetchTags()
})

const totalPages = computed(() => Math.ceil(store.total / store.itemsPerPage))

const formatDate = (dateString: string) => {
  return dateString ? format(new Date(dateString), 'yyyy-MM-dd HH:mm') : 'N/A'
}

const getSortIcon = (column: string) => {
  if (store.sortBy !== column) return ChevronsUpDown
  return store.sortOrder === 'asc' ? ArrowUp : ArrowDown
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
            <div class="relative w-full max-w-sm">
              <Input v-model="store.searchQuery" placeholder="搜索标题或描述..." @keyup.enter="store.search" />
              <Search class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="outline">
                  标签: {{ store.selectedTags.length > 0 ? `${store.selectedTags.length} 已选` : '全部' }}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem v-for="tag in store.tags" :key="tag.id" @click="store.toggleTag(tag.name)">
                  <span :class="['mr-2', store.selectedTags.includes(tag.name) ? 'font-bold' : '']">{{ tag.name }}</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead @click="store.setSort('title')" class="cursor-pointer">
                  标题 <component :is="getSortIcon('title')" class="inline w-4 h-4 ml-1" />
                </TableHead>
                <TableHead>平台</TableHead>
                <TableHead>作者</TableHead>
                <TableHead>标签</TableHead>
                <TableHead @click="store.setSort('favorited_at')" class="cursor-pointer">
                  收藏于 <component :is="getSortIcon('favorited_at')" class="inline w-4 h-4 ml-1" />
                </TableHead>
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
                <TableRow v-for="item in store.items" :key="item.id">
                  <TableCell class="font-medium">{{ item.title }}</TableCell>
                  <TableCell class="capitalize">{{ item.platform }}</TableCell>
                  <TableCell>{{ item.author_name }}</TableCell>
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
            <template v-for="(page, index) in pages">
              <PaginationItem v-if="page.type === 'page'" :key="index" :value="page.value" as-child>
                <Button class="w-10 h-10 p-0" :variant="page.value === store.currentPage ? 'default' : 'outline'">
                  {{ page.value }}
                </Button>
              </PaginationItem>
              <PaginationEllipsis v-else :key="page.type" :index="index" />
            </template>
            <PaginationNext />
            <PaginationLast />
          </Pagination>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>
