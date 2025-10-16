<script setup lang="ts">
/**
 * 通用工坊组件
 *
 * 功能特性：
 * - 收藏项分页浏览（每页20项）
 * - 收藏项详细信息展示（简介、标签、封面、原链接）
 * - AI 结果实时显示（支持增强版 Markdown 渲染）
 * - 历史版本管理（折叠展示历史结果）
 *
 * 数据来源：
 * - workshopsStore: 工坊配置和任务状态
 * - collectionsStore: 收藏项列表
 */

import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkshopsStore } from '@/stores/workshops'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { useCollectionsStore } from '@/stores/collections'
import type { Workshop } from '@/types/api'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  Settings,
  Maximize2,
  X,
  ChevronDown,
  History,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Info,
  Hash,
  Calendar,
  User,
  Search,
  XCircle,
  Bell
} from 'lucide-vue-next'
import WorkshopNotificationConfig from '@/components/workshops/WorkshopNotificationConfig.vue'
import { useToast } from '@/composables/use-toast'

const props = defineProps<{ workshop: Workshop }>()

const route = useRoute()
const router = useRouter()
const workshopsStore = useWorkshopsStore()
const collectionsStore = useCollectionsStore()
const { toast } = useToast()

// ============================================================================
// 收藏项数据（独立管理，获取所有数据）
// ============================================================================
const allItems = ref<any[]>([])
const itemsLoading = ref(false)
const itemsError = ref<string | null>(null)
const searchQuery = ref('')

/**
 * 获取所有收藏项（循环分页获取）
 *
 * 由于后端限制单次最多返回 100 项，需要循环分页获取所有数据
 *
 * 算法：
 * 1. 第一次请求获取第一页（size=100）和 total
 * 2. 根据 total 计算总页数
 * 3. 并发请求剩余所有页
 * 4. 合并所有结果
 */
const fetchAllItems = async () => {
  itemsLoading.value = true
  itemsError.value = null

  try {
    const pageSize = 100  // 后端限制最大值
    const sortBy = 'favorited_at'
    const sortOrder = 'desc'

    // 第一次请求：获取第一页和总数
    const firstResponse = await api.get<any>('/collections', {
      page: 1,
      size: pageSize,
      sort_by: sortBy,
      sort_order: sortOrder
    })

    const total = firstResponse.total
    const totalPages = Math.ceil(total / pageSize)

    console.log(`Total items: ${total}, Total pages: ${totalPages}`)

    // 如果只有一页，直接返回
    if (totalPages <= 1) {
      allItems.value = firstResponse.items.map((it: any) => ({
        ...it,
        author_name: it.author?.username || '',
        url: it.platform === 'bilibili' ? `https://www.bilibili.com/video/${it.platform_item_id}` : undefined,
        description: it.intro,
      }))
      return
    }

    // 并发请求剩余页面（从第2页到最后一页）
    const remainingPages = Array.from({ length: totalPages - 1 }, (_, i) => i + 2)
    const remainingRequests = remainingPages.map(page =>
      api.get<any>('/collections', {
        page,
        size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder
      })
    )

    // 等待所有请求完成
    const remainingResponses = await Promise.all(remainingRequests)

    // 合并所有结果（第一页 + 剩余页）
    const allResponses = [firstResponse, ...remainingResponses]
    const allItemsRaw = allResponses.flatMap(response => response.items)

    // 数据转换
    allItems.value = allItemsRaw.map((it: any) => ({
      ...it,
      author_name: it.author?.username || '',
      url: it.platform === 'bilibili' ? `https://www.bilibili.com/video/${it.platform_item_id}` : undefined,
      description: it.intro,
    }))

    console.log(`Loaded ${allItems.value.length} items from ${totalPages} pages`)
  } catch (error) {
    itemsError.value = error instanceof Error ? error.message : '获取收藏项失败'
    console.error('Failed to fetch all items:', error)
  } finally {
    itemsLoading.value = false
  }
}

// ============================================================================
// 搜索和过滤
// ============================================================================
const filteredItems = computed(() => {
  if (!searchQuery.value.trim()) {
    return allItems.value
  }

  const query = searchQuery.value.toLowerCase()
  return allItems.value.filter((item) => {
    // 搜索标题、简介、作者名
    const matchesTitle = item.title?.toLowerCase().includes(query)
    const matchesIntro = item.intro?.toLowerCase().includes(query)
    const matchesAuthor = item.author?.username?.toLowerCase().includes(query)

    return matchesTitle || matchesIntro || matchesAuthor
  })
})

// ============================================================================
// 分页状态
// ============================================================================
const currentPage = ref(1)
const pageSize = 20

// 分页后的收藏项列表（基于过滤后的结果）
const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return filteredItems.value.slice(start, end)
})

// 当前选中的item（用于在列表中高亮或置顶显示）
const selectedItem = computed(() => {
  if (!selectedItemId.value) return null
  return allItems.value.find(item => item.id === selectedItemId.value)
})

// 检查当前选中的item是否在当前分页中
const isSelectedItemInCurrentPage = computed(() => {
  if (!selectedItemId.value) return false
  return paginatedItems.value.some(item => item.id === selectedItemId.value)
})

// 总页数（基于过滤后的结果）
const totalPages = computed(() => {
  return Math.ceil(filteredItems.value.length / pageSize)
})

// 重置搜索
const resetSearch = () => {
  searchQuery.value = ''
  currentPage.value = 1
}

// 监听搜索词变化，重置到第一页
watch(searchQuery, () => {
  currentPage.value = 1
})

// 跳转到包含选中item的页面
const jumpToSelectedItemPage = () => {
  if (!selectedItemId.value) return

  const index = filteredItems.value.findIndex(item => item.id === selectedItemId.value)
  if (index === -1) {
    // 如果在过滤结果中找不到，清除搜索后再试
    searchQuery.value = ''
    // 等待下一个tick后再查找
    nextTick(() => {
      const newIndex = filteredItems.value.findIndex(item => item.id === selectedItemId.value)
      if (newIndex !== -1) {
        currentPage.value = Math.floor(newIndex / pageSize) + 1
      }
    })
  } else {
    currentPage.value = Math.floor(index / pageSize) + 1
  }
}

// 是否有上一页/下一页
const hasPrevPage = computed(() => currentPage.value > 1)
const hasNextPage = computed(() => currentPage.value < totalPages.value)

// 翻页操作
const goToPrevPage = () => {
  if (hasPrevPage.value) currentPage.value--
}
const goToNextPage = () => {
  if (hasNextPage.value) currentPage.value++
}

// ============================================================================
// 工坊配置
// ============================================================================
const name = ref(props.workshop.name)
const systemPrompt = ref<string | undefined>((props.workshop as any).default_prompt || props.workshop.system_prompt)
const userPrompt = ref<string | undefined>(props.workshop.user_prompt_template)

// Keep local state in sync if the prop changes (e.g., after fetch)
watch(
  () => props.workshop,
  (wk) => {
    if (!wk) return
    name.value = wk.name
    // prefer unified field
    // @ts-ignore
    systemPrompt.value = (wk as any).default_prompt || (wk as any).system_prompt
    userPrompt.value = (wk as any).user_prompt_template
  },
  { deep: true }
)

// ============================================================================
// 对话框和状态
// ============================================================================
const saving = ref(false)
const running = ref(false)
const selectedItemId = ref<number | null>(
  route.query.item ? parseInt(route.query.item as string) : null
)
const activeTaskId = ref<string | null>(null)
const selectedItemDetails = ref<any>(null)

// 弹窗状态
const promptDialogOpen = ref(false)
const resultDetailDialogOpen = ref(false)
const itemDetailDialogOpen = ref(false)  // 新增：收藏项详情弹窗
const notificationConfigDialogOpen = ref(false)  // 新增：通知配置弹窗
const selectedResult = ref<any>(null)
const historyExpanded = ref(false)

const existingResults = computed(() => {
  if (!selectedItemDetails.value?.results) {
    console.log('No results in selectedItemDetails')
    return []
  }
  const workshopId = (props.workshop as any).workshop_id || (props.workshop as any).id
  console.log('Filtering results for workshop:', workshopId)
  console.log('All results:', selectedItemDetails.value.results)
  
  // Filter results for this workshop and sort by created_at desc
  const filtered = selectedItemDetails.value.results
    .filter((r: any) => {
      console.log('Checking result:', r.workshop_id, 'against', workshopId)
      return r.workshop_id === workshopId
    })
    .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  
  console.log('Filtered results:', filtered)
  return filtered
})

// 最新结果（默认展示）
const latestResult = computed(() => {
  const result = existingResults.value[0] || null
  console.log('Latest result:', result)
  return result
})

// 历史版本（除了最新的）
const historicalResults = computed(() => existingResults.value.slice(1))

// 当前任务状态
const currentTaskStatus = computed(() => {
  if (!activeTaskId.value) return null
  return workshopsStore.tasks[activeTaskId.value]?.status || 'pending'
})

// 是否正在生成中
const isGenerating = computed(() => {
  return activeTaskId.value && (currentTaskStatus.value === 'pending' || currentTaskStatus.value === 'in_progress')
})

// ============================================================================
// 增强版 Markdown 渲染
// ============================================================================

/**
 * 增强版 Markdown 渲染函数
 *
 * 支持的语法：
 * - 标题（# ## ###）
 * - 代码块（```language ... ```）
 * - 行内代码（`code`）
 * - 加粗（**text**）
 * - 斜体（*text*）
 * - 链接（[text](url)）
 * - 图片（![alt](url)）
 * - 引用（> text）
 * - 列表（- item 或 1. item）
 * - 水平分割线（--- 或 ***）
 * - 表格（| col1 | col2 |）
 *
 * 注意：这是临时方案，生产环境建议使用 marked + DOMPurify
 */
const renderMarkdown = (text: string): string => {
  if (!text) return ''

  let html = text

  // 1. 代码块（必须最先处理，避免内部内容被误解析）
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
    const language = lang || 'plaintext'
    const escapedCode = code
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
    return `<pre class="bg-muted/50 rounded-md p-4 overflow-x-auto my-4 border border-border"><code class="text-sm font-mono language-${language}">${escapedCode}</code></pre>`
  })

  // 2. 表格
  html = html.replace(/^\|(.+)\|\n\|[-:\s|]+\|\n((?:\|.+\|\n?)*)/gm, (match, header, rows) => {
    const headers = header.split('|').filter((h: string) => h.trim()).map((h: string) =>
      `<th class="border border-border px-4 py-2 bg-muted/50 font-semibold">${h.trim()}</th>`
    ).join('')

    const rowsHtml = rows.trim().split('\n').map((row: string) => {
      const cells = row.split('|').filter((c: string) => c.trim()).map((c: string) =>
        `<td class="border border-border px-4 py-2">${c.trim()}</td>`
      ).join('')
      return `<tr>${cells}</tr>`
    }).join('')

    return `<table class="w-full my-4 border-collapse border border-border rounded-md overflow-hidden"><thead><tr>${headers}</tr></thead><tbody>${rowsHtml}</tbody></table>`
  })

  // 3. 引用块
  html = html.replace(/^> (.+)$/gm, '<blockquote class="border-l-4 border-primary pl-4 py-2 my-4 text-muted-foreground italic bg-muted/30">$1</blockquote>')

  // 4. 水平分割线
  html = html.replace(/^(---|\*\*\*)$/gm, '<hr class="my-6 border-border" />')

  // 5. 标题（### → h3, ## → h2, # → h1）
  html = html.replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-6 mb-3 scroll-mt-20">$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold mt-8 mb-4 scroll-mt-20">$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mt-10 mb-5 scroll-mt-20">$1</h1>')

  // 6. 有序列表
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="ml-6 my-1 list-decimal">$1</li>')

  // 7. 无序列表
  html = html.replace(/^- (.+)$/gm, '<li class="ml-6 my-1 list-disc">$1</li>')

  // 8. 图片（![alt](url)）
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="max-w-full h-auto rounded-md my-4 shadow-sm" />')

  // 9. 链接（[text](url)）
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline font-medium">$1 <ExternalLink class="inline h-3 w-3" /></a>')

  // 10. 行内代码（`code`）
  html = html.replace(/`([^`]+)`/g, '<code class="bg-muted px-1.5 py-0.5 rounded text-sm font-mono border border-border">$1</code>')

  // 11. 加粗（**text**）
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="font-bold">$1</strong>')

  // 12. 斜体（*text*）
  html = html.replace(/\*(.+?)\*/g, '<em class="italic">$1</em>')

  // 13. 换行
  html = html.replace(/\n/g, '<br />')

  return html
}

// ============================================================================
// 弹窗操作
// ============================================================================

/**
 * 查看 AI 结果详情（全屏弹窗）
 */
const viewResultDetail = (result: any) => {
  selectedResult.value = result
  resultDetailDialogOpen.value = true
}

/**
 * 查看收藏项详情（全屏弹窗）
 */
const viewItemDetail = () => {
  if (selectedItemDetails.value) {
    itemDetailDialogOpen.value = true
  }
}

/**
 * 打开原链接
 */
const openOriginalUrl = (url?: string) => {
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

const saveChanges = async () => {
  saving.value = true
  try {
    const workshopId = (props.workshop as any).workshop_id || (props.workshop as any).id
    await workshopsStore.updateWorkshop(workshopId, {
      name: name.value,
      // backend unified fields only
      // @ts-ignore
      default_prompt: systemPrompt.value || userPrompt.value || '',
    } as any)

    // 重新从服务器加载工坊数据以确保本地状态同步
    await workshopsStore.fetchWorkshopBySlug(workshopId)

    // 显示成功提示
    toast({
      title: '保存成功',
      description: '工坊配置已更新',
    })
  } catch (error) {
    // 显示错误提示
    toast({
      title: '保存失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    })
  } finally {
    saving.value = false
  }
}

const execute = async () => {
  if (selectedItemId.value == null) return
  running.value = true
  try {
    const taskId = await workshopsStore.executeWorkshop(
      (props.workshop as any).workshop_id || (props.workshop as any).id,
      selectedItemId.value,
      {
        // Only send prompt if provided; backend also supports llm_model
        prompt: userPrompt.value || systemPrompt.value || undefined,
      }
    )
    if (taskId) {
      activeTaskId.value = taskId
      workshopsStore.subscribeToTask(taskId)
    }
  } finally {
    running.value = false
  }
}

// Watch for selected item changes and fetch details
watch(selectedItemId, async (newId, oldId) => {
  // 切换收藏项时清空当前任务状态
  activeTaskId.value = null
  
  // Update URL query parameter
  if (newId !== oldId) {
    const query = newId ? { item: newId.toString() } : {}
    router.replace({ query })
  }
  
  if (newId) {
    try {
      selectedItemDetails.value = await api.get(`/collections/${newId}`)
    } catch (error) {
      console.error('Failed to fetch item details:', error)
    }
  } else {
    selectedItemDetails.value = null
  }
})

// Watch for URL query changes (e.g., from browser back/forward)
watch(
  () => route.query.item,
  (itemQuery) => {
    const itemId = itemQuery ? parseInt(itemQuery as string) : null
    if (itemId !== selectedItemId.value) {
      selectedItemId.value = itemId
    }
  }
)

// 监听任务状态，完成后清空 activeTaskId
watch(
  () => activeTaskId.value ? workshopsStore.tasks[activeTaskId.value]?.status : null,
  (status) => {
    if (status === 'success' || status === 'failure') {
      // 任务完成，延迟清空以便用户看到最终状态
      setTimeout(() => {
        activeTaskId.value = null
        // 刷新详情以获取新生成的结果
        if (selectedItemId.value) {
          api.get(`/collections/${selectedItemId.value}`).then(data => {
            selectedItemDetails.value = data
          })
        }
      }, 1000)
    }
  }
)

onMounted(async () => {
  // 获取所有收藏项
  await fetchAllItems()

  // If URL has item query, load its details immediately
  if (selectedItemId.value) {
    try {
      selectedItemDetails.value = await api.get(`/collections/${selectedItemId.value}`)
      console.log('Loaded item from URL:', selectedItemDetails.value)
      console.log('Existing results:', existingResults.value)
    } catch (error) {
      console.error('Failed to load item from URL:', error)
    }
  }
})
</script>

<template>
  <div class="fixed inset-0 left-0 md:left-64 flex flex-col bg-background">
    <header class="p-4 border-b border-border bg-muted/50 flex items-center justify-between shrink-0">
      <h2 class="text-2xl font-bold tracking-tight">{{ name }}</h2>
      <div class="flex items-center gap-2">
        <!-- 提示词配置 -->
        <Dialog v-model:open="promptDialogOpen">
        <DialogTrigger as-child>
          <Button size="sm" variant="outline">
            <Settings class="w-4 h-4 mr-2" />
            提示词配置
          </Button>
        </DialogTrigger>
        <DialogContent class="max-w-2xl">
          <DialogHeader>
            <DialogTitle>提示词配置</DialogTitle>
          </DialogHeader>
          <div class="space-y-4 py-4">
            <div class="space-y-2">
              <label class="text-sm font-medium">系统提示词</label>
              <textarea v-model="systemPrompt" rows="6" class="w-full border rounded-md p-3 text-sm resize-none"></textarea>
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium">用户提示模板</label>
              <textarea v-model="userPrompt" rows="6" class="w-full border rounded-md p-3 text-sm resize-none"></textarea>
            </div>
            <div class="flex justify-end gap-2">
              <Button variant="outline" @click="promptDialogOpen = false">取消</Button>
              <Button @click="saveChanges(); promptDialogOpen = false" :disabled="saving">
                {{ saving ? '保存中...' : '保存' }}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

        <!-- 通知配置 -->
        <Dialog v-model:open="notificationConfigDialogOpen">
          <DialogTrigger as-child>
            <Button size="sm" variant="outline">
              <Bell class="w-4 h-4 mr-2" />
              通知配置
            </Button>
          </DialogTrigger>
          <DialogContent class="max-w-2xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>通知配置</DialogTitle>
            </DialogHeader>
            <WorkshopNotificationConfig
              :workshop-id="(props.workshop as any).workshop_id || (props.workshop as any).id"
              @saved="notificationConfigDialogOpen = false"
            />
          </DialogContent>
        </Dialog>
      </div>
    </header>

    <div class="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-px bg-border min-h-0 overflow-hidden">
      <!-- 左侧：源材料选择（固定高度，内部滚动）-->
      <div class="bg-background flex flex-col h-full overflow-hidden">
        <!-- 头部：标题 + 刷新按钮 -->
        <div class="p-4 border-b border-border shrink-0 space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <h3 class="font-semibold">选择收藏项目</h3>
              <Badge variant="outline" class="text-xs">
                {{ filteredItems.length }} / {{ allItems.length }} 项
              </Badge>
            </div>
            <Button size="sm" variant="outline" @click="fetchAllItems()" :disabled="itemsLoading">
              {{ itemsLoading ? '加载中...' : '刷新' }}
            </Button>
            <Button size="sm" :disabled="!selectedItemId || running" @click="execute">
              {{ running ? '执行中...' : '执行工坊' }}
            </Button>
          </div>

          <!-- 搜索框 -->
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <Input
              v-model="searchQuery"
              placeholder="搜索标题、简介或作者..."
              class="pl-10 pr-10"
            />
            <Button
              v-if="searchQuery"
              size="sm"
              variant="ghost"
              class="absolute right-1 top-1/2 -translate-y-1/2 h-7 px-2"
              @click="resetSearch"
            >
              <XCircle class="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        <!-- 收藏项列表（分页 + 固定高度滚动）-->
        <div class="flex-1 overflow-y-auto p-4 space-y-3">
          <!-- 当前选中的item（如果不在当前分页中，置顶显示）-->
          <div v-if="selectedItem && !isSelectedItemInCurrentPage" class="mb-4">
            <div class="flex items-center justify-between gap-2 mb-2">
              <div class="flex items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="default" class="text-xs">当前选中</Badge>
                <span>该项不在当前页中</span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                class="h-6 text-xs"
                @click="jumpToSelectedItemPage"
              >
                跳转到该页
              </Button>
            </div>
            <Card
              class="cursor-pointer shadow-md ring-2 ring-primary bg-primary/5"
              @click="selectedItemId = selectedItem.id"
            >
              <CardContent class="p-4 space-y-3">
                <!-- 标题 -->
                <div class="flex items-start justify-between gap-2">
                  <h4 class="text-sm font-medium line-clamp-2 flex-1">{{ selectedItem.title }}</h4>
                  <Badge :variant="selectedItem.status === 'processed' ? 'default' : 'outline'" class="text-xs shrink-0">
                    {{ selectedItem.status === 'processed' ? '已处理' : selectedItem.status === 'pending' ? '待处理' : '失败' }}
                  </Badge>
                </div>

                <!-- 简介 -->
                <p v-if="selectedItem.intro" class="text-xs text-muted-foreground line-clamp-2">
                  {{ selectedItem.intro }}
                </p>

                <!-- 元数据 -->
                <div class="flex items-center gap-3 text-xs text-muted-foreground">
                  <Badge variant="secondary" class="text-xs capitalize">
                    {{ selectedItem.platform }}
                  </Badge>
                  <div v-if="selectedItem.author" class="flex items-center gap-1">
                    <User class="h-3 w-3" />
                    <span>{{ selectedItem.author.username }}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <!-- 当前分页的items -->
          <Card
            v-for="item in paginatedItems"
            :key="item.id"
            class="cursor-pointer hover:shadow-md transition-all"
            :class="selectedItemId === item.id ? 'ring-2 ring-primary bg-primary/5' : ''"
            @click="selectedItemId = item.id"
          >
            <CardContent class="p-4 space-y-3">
              <!-- 标题 -->
              <div class="flex items-start justify-between gap-2">
                <h4 class="text-sm font-medium line-clamp-2 flex-1">{{ item.title }}</h4>
                <Badge :variant="item.status === 'processed' ? 'default' : 'outline'" class="text-xs shrink-0">
                  {{ item.status === 'processed' ? '已处理' : item.status === 'pending' ? '待处理' : '失败' }}
                </Badge>
              </div>

              <!-- 简介 -->
              <p v-if="item.intro" class="text-xs text-muted-foreground line-clamp-2">
                {{ item.intro }}
              </p>

              <!-- 元数据：平台、作者、日期 -->
              <div class="flex items-center gap-3 text-xs text-muted-foreground">
                <div class="flex items-center gap-1">
                  <Badge variant="secondary" class="text-xs capitalize">
                    {{ item.platform }}
                  </Badge>
                </div>
                <div v-if="item.author" class="flex items-center gap-1">
                  <User class="h-3 w-3" />
                  <span>{{ item.author.username }}</span>
                </div>
              </div>

              <!-- 标签 -->
              <div v-if="item.tags && item.tags.length > 0" class="flex flex-wrap gap-1">
                <Badge
                  v-for="tag in item.tags.slice(0, 3)"
                  :key="tag.id"
                  variant="outline"
                  class="text-xs"
                >
                  <Hash class="h-2.5 w-2.5 mr-0.5" />
                  {{ tag.name }}
                </Badge>
                <Badge v-if="item.tags.length > 3" variant="outline" class="text-xs">
                  +{{ item.tags.length - 3 }}
                </Badge>
              </div>

              <!-- 操作按钮 -->
              <div class="flex items-center gap-2 pt-2">
                <Button
                  v-if="item.url"
                  size="sm"
                  variant="ghost"
                  class="h-7 text-xs"
                  @click.stop="openOriginalUrl(item.url)"
                >
                  <ExternalLink class="h-3 w-3 mr-1" />
                  打开原链接
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  class="h-7 text-xs"
                  @click.stop="selectedItemId = item.id; viewItemDetail()"
                >
                  <Info class="h-3 w-3 mr-1" />
                  查看详情
                </Button>
              </div>
            </CardContent>
          </Card>

          <!-- 加载状态 -->
          <div v-if="itemsLoading && allItems.length === 0" class="text-center py-8">
            <p class="text-sm text-muted-foreground">加载中...</p>
          </div>

          <!-- 搜索无结果 -->
          <div v-else-if="!itemsLoading && searchQuery && filteredItems.length === 0" class="text-center py-8">
            <p class="text-sm text-muted-foreground mb-2">未找到匹配的收藏项</p>
            <Button size="sm" variant="outline" @click="resetSearch">
              清除搜索
            </Button>
          </div>

          <!-- 空状态 -->
          <div v-else-if="!itemsLoading && allItems.length === 0" class="text-center py-8">
            <p class="text-sm text-muted-foreground">暂无收藏项</p>
          </div>
        </div>

        <!-- 分页控件 -->
        <div v-if="totalPages > 1" class="p-3 border-t border-border shrink-0">
          <div class="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>第 {{ currentPage }} / {{ totalPages }} 页</span>
            <span>共 {{ filteredItems.length }} 项{{ searchQuery ? ` (已过滤)` : '' }}</span>
          </div>
          <div class="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              class="flex-1"
              :disabled="!hasPrevPage"
              @click="goToPrevPage"
            >
              <ChevronLeft class="h-4 w-4 mr-1" />
              上一页
            </Button>
            <Button
              size="sm"
              variant="outline"
              class="flex-1"
              :disabled="!hasNextPage"
              @click="goToNextPage"
            >
              下一页
              <ChevronRight class="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      </div>

      <!-- 右侧：结果显示（占据更大空间，内容自然展示）-->
      <div class="lg:col-span-2 bg-background flex h-full overflow-hidden">
        <div class="p-4 border-b border-border shrink-0">
          <h3 class="font-semibold">AI 生成结果</h3>
          
        </div>

        <div class="flex-1 overflow-y-auto">
          <!-- 当前任务结果（正在生成）-->
          <div v-if="isGenerating" class="border-b p-6 bg-primary/5">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2">
                <Badge class="text-xs">⚡ 正在生成</Badge>
                <Badge variant="outline" class="text-xs">{{ currentTaskStatus }}</Badge>
              </div>
              <span class="text-xs text-muted-foreground font-mono">{{ activeTaskId }}</span>
            </div>
            <div 
              class="prose dark:prose-invert max-w-none" 
              v-html="renderMarkdown(workshopsStore.tasks[activeTaskId!]?.result?.content || '等待结果...')"
            />
          </div>

          <!-- 最新版本（完整展示）-->
          <div v-if="latestResult" class="p-6 border-b">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2">
                <Badge variant="default" class="text-xs">最新版本</Badge>
                <span class="text-xs text-muted-foreground">
                  {{ new Date(latestResult.created_at).toLocaleString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
                </span>
              </div>
              <Button size="sm" variant="ghost" @click="viewResultDetail(latestResult)">
                <Maximize2 class="h-4 w-4 mr-2" />
                全屏查看
              </Button>
            </div>
            <div 
              class="prose dark:prose-invert max-w-none" 
              v-html="renderMarkdown(latestResult.content)"
            />
          </div>

          <!-- 历史版本（折叠）-->
          <Collapsible v-if="historicalResults.length > 0" v-model:open="historyExpanded" class="border-b">
            <CollapsibleTrigger class="w-full p-4 hover:bg-muted/50 transition-colors flex items-center justify-between">
              <div class="flex items-center gap-2">
                <History class="h-4 w-4 text-muted-foreground" />
                <span class="text-sm font-medium">历史版本</span>
                <Badge variant="outline" class="text-xs">{{ historicalResults.length }}</Badge>
              </div>
              <ChevronDown 
                class="h-4 w-4 text-muted-foreground transition-transform" 
                :class="{ 'rotate-180': historyExpanded }"
              />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div class="p-4 space-y-3 bg-muted/20">
                <Card 
                  v-for="(result, index) in historicalResults" 
                  :key="result.id" 
                  class="cursor-pointer hover:shadow-md transition-shadow"
                  @click="viewResultDetail(result)"
                >
                  <CardContent class="p-4">
                    <div class="flex items-center justify-between mb-3">
                      <Badge variant="outline" class="text-xs">版本 #{{ historicalResults.length - index }}</Badge>
                      <div class="flex items-center gap-2">
                        <span class="text-xs text-muted-foreground">
                          {{ new Date(result.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
                        </span>
                        <Button size="icon" variant="ghost" class="h-6 w-6">
                          <Maximize2 class="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    <div 
                      class="prose prose-sm dark:prose-invert max-w-none line-clamp-3" 
                      v-html="renderMarkdown(result.content)"
                    />
                  </CardContent>
                </Card>
              </div>
            </CollapsibleContent>
          </Collapsible>

          <!-- 空状态 -->
          <div v-if="!latestResult && !isGenerating" class="flex items-center justify-center p-8 min-h-[400px]">
            <p class="text-sm text-muted-foreground text-center">
              {{ selectedItemId ? '该项目暂无结果，点击执行按钮生成。' : '选择一个收藏项目开始。' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果详情弹窗 -->
    <Dialog v-model:open="resultDetailDialogOpen">
      <DialogContent class="max-w-4xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <div class="flex items-center justify-between">
            <DialogTitle>AI 结果详情</DialogTitle>
            <div class="flex items-center gap-2">
              <Badge variant="outline" class="text-xs">
                {{ new Date(selectedResult?.created_at).toLocaleString('zh-CN') }}
              </Badge>
            </div>
          </div>
        </DialogHeader>
        <ScrollArea class="flex-1 -mx-6 px-6 py-4">
          <div
            class="prose dark:prose-invert max-w-none prose-headings:scroll-mt-20"
            v-html="renderMarkdown(selectedResult?.content || '')"
          />
        </ScrollArea>
      </DialogContent>
    </Dialog>

    <!-- 收藏项详情弹窗 -->
    <Dialog v-model:open="itemDetailDialogOpen">
      <DialogContent class="max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>收藏项详情</DialogTitle>
        </DialogHeader>

        <ScrollArea v-if="selectedItemDetails" class="flex-1 -mx-6 px-6 py-4">
          <div class="space-y-6">
            <!-- 封面图 -->
            <div v-if="selectedItemDetails.cover_url" class="w-full">
              <img
                :src="selectedItemDetails.cover_url"
                :alt="selectedItemDetails.title"
                class="w-full h-auto rounded-lg shadow-md object-cover max-h-80"
              />
            </div>

            <!-- 基本信息 -->
            <div class="space-y-4">
              <div>
                <h3 class="text-xl font-bold mb-2">{{ selectedItemDetails.title }}</h3>
                <div class="flex items-center gap-3 text-sm text-muted-foreground">
                  <Badge variant="secondary" class="capitalize">
                    {{ selectedItemDetails.platform }}
                  </Badge>
                  <div v-if="selectedItemDetails.author" class="flex items-center gap-1">
                    <User class="h-3.5 w-3.5" />
                    <span>{{ selectedItemDetails.author.username }}</span>
                  </div>
                  <Badge
                    :variant="selectedItemDetails.status === 'processed' ? 'default' : 'outline'"
                  >
                    {{ selectedItemDetails.status === 'processed' ? '已处理' : selectedItemDetails.status === 'pending' ? '待处理' : '失败' }}
                  </Badge>
                </div>
              </div>

              <!-- 简介 -->
              <div v-if="selectedItemDetails.intro">
                <h4 class="text-sm font-semibold mb-2 text-muted-foreground">简介</h4>
                <p class="text-sm leading-relaxed">{{ selectedItemDetails.intro }}</p>
              </div>

              <!-- 标签 -->
              <div v-if="selectedItemDetails.tags && selectedItemDetails.tags.length > 0">
                <h4 class="text-sm font-semibold mb-2 text-muted-foreground">标签</h4>
                <div class="flex flex-wrap gap-2">
                  <Badge
                    v-for="tag in selectedItemDetails.tags"
                    :key="tag.id"
                    variant="outline"
                  >
                    <Hash class="h-3 w-3 mr-1" />
                    {{ tag.name }}
                  </Badge>
                </div>
              </div>

              <!-- 时间信息 -->
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div v-if="selectedItemDetails.published_at">
                  <div class="flex items-center gap-1 text-muted-foreground mb-1">
                    <Calendar class="h-3.5 w-3.5" />
                    <span class="font-medium">发布时间</span>
                  </div>
                  <p>{{ new Date(selectedItemDetails.published_at).toLocaleString('zh-CN') }}</p>
                </div>
                <div>
                  <div class="flex items-center gap-1 text-muted-foreground mb-1">
                    <Calendar class="h-3.5 w-3.5" />
                    <span class="font-medium">收藏时间</span>
                  </div>
                  <p>{{ new Date(selectedItemDetails.favorited_at).toLocaleString('zh-CN') }}</p>
                </div>
              </div>

              <!-- 所属合集 -->
              <div v-if="selectedItemDetails.collection">
                <h4 class="text-sm font-semibold mb-2 text-muted-foreground">所属合集</h4>
                <Card>
                  <CardContent class="p-3">
                    <p class="font-medium text-sm">{{ selectedItemDetails.collection.name }}</p>
                    <p v-if="selectedItemDetails.collection.description" class="text-xs text-muted-foreground mt-1">
                      {{ selectedItemDetails.collection.description }}
                    </p>
                    <p class="text-xs text-muted-foreground mt-1">
                      共 {{ selectedItemDetails.collection.item_count }} 项
                    </p>
                  </CardContent>
                </Card>
              </div>

              <!-- 平台详情（如果有） -->
              <div v-if="selectedItemDetails.details">
                <h4 class="text-sm font-semibold mb-2 text-muted-foreground">平台详情</h4>
                <div class="bg-muted/30 rounded-lg p-4 space-y-2 text-sm">
                  <div v-if="selectedItemDetails.details.view_count" class="flex justify-between">
                    <span class="text-muted-foreground">播放量</span>
                    <span class="font-medium">{{ selectedItemDetails.details.view_count.toLocaleString() }}</span>
                  </div>
                  <div v-if="selectedItemDetails.details.like_count" class="flex justify-between">
                    <span class="text-muted-foreground">点赞数</span>
                    <span class="font-medium">{{ selectedItemDetails.details.like_count.toLocaleString() }}</span>
                  </div>
                  <div v-if="selectedItemDetails.details.coin_count" class="flex justify-between">
                    <span class="text-muted-foreground">投币数</span>
                    <span class="font-medium">{{ selectedItemDetails.details.coin_count.toLocaleString() }}</span>
                  </div>
                  <div v-if="selectedItemDetails.details.favorite_count" class="flex justify-between">
                    <span class="text-muted-foreground">收藏数</span>
                    <span class="font-medium">{{ selectedItemDetails.details.favorite_count.toLocaleString() }}</span>
                  </div>
                  <div v-if="selectedItemDetails.details.duration" class="flex justify-between">
                    <span class="text-muted-foreground">时长</span>
                    <span class="font-medium">{{ Math.floor(selectedItemDetails.details.duration / 60) }} 分钟</span>
                  </div>
                </div>
              </div>

              <!-- 字幕（前100行） -->
              <div v-if="selectedItemDetails.details?.subtitles && selectedItemDetails.details.subtitles.length > 0">
                <h4 class="text-sm font-semibold mb-2 text-muted-foreground">字幕预览</h4>
                <ScrollArea class="h-64 bg-muted/30 rounded-lg p-4">
                  <div class="space-y-1 text-xs font-mono">
                    <div
                      v-for="(sub, index) in selectedItemDetails.details.subtitles.slice(0, 100)"
                      :key="index"
                      class="flex gap-3"
                    >
                      <span class="text-muted-foreground shrink-0">{{ index + 1 }}</span>
                      <span>{{ sub.text }}</span>
                    </div>
                    <p v-if="selectedItemDetails.details.subtitles.length > 100" class="text-muted-foreground italic pt-2">
                      ... 还有 {{ selectedItemDetails.details.subtitles.length - 100 }} 行
                    </p>
                  </div>
                </ScrollArea>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex items-center gap-2 pt-4 border-t">
              <Button
                v-if="selectedItemDetails.url"
                variant="default"
                @click="openOriginalUrl(selectedItemDetails.url)"
                class="flex-1"
              >
                <ExternalLink class="h-4 w-4 mr-2" />
                打开原链接
              </Button>
              <Button
                variant="outline"
                @click="itemDetailDialogOpen = false"
                class="flex-1"
              >
                关闭
              </Button>
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  </div>
</template>
