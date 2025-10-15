<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useWorkshopsStore } from '@/stores/workshops'
import type { Workshop } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '@/components/ui/dropdown-menu'
import WorkshopConfigForm from '@/components/workshops/WorkshopConfigForm.vue'
import { useRouter } from 'vue-router'
import { Badge } from '@/components/ui/badge'
import { Image as ImageIcon, Sparkles, Search, Filter, Activity, FlaskConical, Swords, BookOpen, MoreVertical } from 'lucide-vue-next'
import { Switch } from '@/components/ui/switch'

const store = useWorkshopsStore()
const router = useRouter()

onMounted(() => {  
  store.fetchWorkshops()
})

const workshops = computed(() => store.workshops)
const q = ref('')
const onlyListening = ref(false)
const filtered = computed(() => {
  const term = q.value.trim().toLowerCase()
  const list = store.workshops as any[]
  return list.filter(w => {
    const passText = !term || (w.name?.toLowerCase().includes(term) || w.workshop_id?.toLowerCase().includes(term))
    const passListen = !onlyListening.value || w.executor_config?.listening_enabled === true
    return passText && passListen
  })
})
const isLoading = computed(() => store.loading)

// icon palette mapping (id -> icon + color)
const iconMap: Record<string, any> = {
  'snapshot-insight': { icon: Activity, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  'information-alchemy': { icon: FlaskConical, color: 'text-purple-500', bg: 'bg-purple-500/10' },
  'point-counterpoint': { icon: Swords, color: 'text-orange-500', bg: 'bg-orange-500/10' },
  'summary-01': { icon: BookOpen, color: 'text-green-600', bg: 'bg-green-600/10' },
}
const iconFor = (wk: any) => {
  const key = wk?.workshop_id
  return iconMap[key] || { icon: Sparkles, color: 'text-primary', bg: 'bg-primary/10' }
}

const isListening = (wk: any) => Boolean(wk?.executor_config?.listening_enabled)

// dialog state
const dialogOpen = ref(false)
// 🔧 关键修复：使用 workshop ID 而不是直接引用对象，避免引用失效
const editingWorkshopId = ref<string | null>(null)

// 🔧 使用 computed 动态获取最新数据，当 store 更新时自动同步
const editingWorkshop = computed(() => {
  if (!editingWorkshopId.value) return null
  return store.getWorkshopBySlug(editingWorkshopId.value)
})

const openCreate = () => {
  editingWorkshopId.value = null
  dialogOpen.value = true
}

const openEdit = (wk: Workshop) => {
  editingWorkshopId.value = (wk as any).workshop_id
  dialogOpen.value = true
}

const handleSaved = () => {
  store.fetchWorkshops()
}

const handleDelete = async (wk: Workshop) => {
  if (confirm(`确定删除工坊 "${wk.name}" ?`)) {
    await store.deleteWorkshop(wk.workshop_id)
  }
}

const goToWorkshop = (workshopSlug: string) => {
  router.push(`/workshops/${workshopSlug}`)
}
</script>

<template>
  <div class="h-full flex flex-col">
    <header class="relative overflow-hidden">
      <div class="absolute inset-0 pointer-events-none">
        <div class="absolute -top-20 -left-10 h-72 w-72 bg-primary/10 blur-3xl rounded-full" />
        <div class="absolute -bottom-20 -right-10 h-72 w-72 bg-purple-500/10 blur-3xl rounded-full" />
      </div>
      <div class="relative z-10 px-6 py-6 md:px-8 md:py-8 border-b border-border">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-3xl font-bold tracking-tight">AI 工作坊</h2>
            <p class="text-sm text-muted-foreground mt-1">选择一个工作坊来处理你的收藏或输入。坚持做减法，只有真正必要的操作被保留。</p>
          </div>
          <Button variant="secondary" size="sm" @click="openCreate">新建工坊</Button>
        </div>
      </div>
    </header>

    <div class="flex-1 overflow-y-auto p-8">
      <!-- Controls -->
      <div class="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div class="flex items-center gap-2 rounded-lg border bg-background/80 backdrop-blur-sm px-3 py-2 md:min-w-[380px]">
          <Search class="w-4 h-4 text-muted-foreground" />
          <input v-model="q" placeholder="搜索名称或 ID…" class="w-full bg-transparent text-sm outline-none" />
        </div>
        <div class="flex items-center gap-4">
          <label class="flex items-center gap-2 select-none text-sm">
            <Filter class="w-4 h-4 text-muted-foreground" />
            仅显示监听中
            <Switch v-model="onlyListening" />
          </label>
        </div>
      </div>

      <!-- Loading state -->
      <div v-if="isLoading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="rounded-xl border bg-card p-4 animate-pulse h-[180px]" />
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card 
          v-for="workshop in filtered" 
          :key="workshop.workshop_id || workshop.id" 
          :class="['group flex flex-col transition-all relative p-[1px] rounded-xl hover:shadow-lg', isListening(workshop) ? 'bg-gradient-to-b from-primary/25 to-transparent ring-1 ring-primary/20' : 'bg-gradient-to-b from-border/60 to-transparent']"
        >
          <div class="rounded-[11px] bg-card h-full flex flex-col">
            <!-- kebab menu -->
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="ghost" size="icon" class="absolute top-2 right-2">
                  <span class="sr-only">菜单</span>
                  <MoreVertical class="w-4 h-4 text-muted-foreground" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem @click="openEdit(workshop)">编辑</DropdownMenuItem>
                <DropdownMenuItem class="text-destructive" @click="handleDelete(workshop)">删除</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <CardHeader class="py-4">
              <div class="flex items-start gap-3">
                <div :class="[iconFor(workshop).bg, 'h-10 w-10 rounded-md flex items-center justify-center shrink-0']">
                  <component :is="iconFor(workshop).icon" :class="[iconFor(workshop).color, 'w-5 h-5']" />
                </div>
                <div class="min-w-0 w-full">
                  <div class="flex items-center justify-between gap-4">
                    <div class="flex items-center gap-2 min-w-0">
                      <span v-if="isListening(workshop)" class="inline-block w-2 h-2 rounded-full bg-primary animate-pulse" />
                      <CardTitle class="truncate">{{ workshop.name }}</CardTitle>
                    </div>
                    <div class="flex items-center gap-2 select-none">
                      <span class="text-xs text-muted-foreground">监听</span>
                      <Switch :model-value="(workshop as any).executor_config?.listening_enabled === true"
                        @update:modelValue="(val: boolean) => store.toggleListening((workshop as any).workshop_id, !!val, (workshop as any).name)" />
                    </div>
                  </div>
                  <CardDescription class="line-clamp-2 min-h-[36px]">{{ workshop.description }}</CardDescription>
                  <div class="mt-2 flex items-center gap-2">
                    <Badge variant="outline" v-if="workshop.executor_type" class="bg-muted/70">{{ workshop.executor_type }}</Badge>
                    <Badge v-if="workshop.default_model" class="bg-muted/70">{{ workshop.default_model }}</Badge>
                    <Badge variant="secondary">{{ (workshop as any).workshop_id }}</Badge>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent class="flex-1 flex items-end py-4">
              <div class="w-full grid grid-cols-2 gap-2">
                <Button as-child variant="secondary" class="transition-colors">
                  <NuxtLink @click="openEdit(workshop)">配置</NuxtLink>
                </Button>
                <Button as-child class="transition-transform group-hover:translate-x-[1px]">
                  <NuxtLink @click="goToWorkshop(workshop.workshop_id)">进入</NuxtLink>
                </Button>
              </div>
            </CardContent>
          </div>
        </Card>
      </div>

      <WorkshopConfigForm :open="dialogOpen" :workshop="editingWorkshop" @update:open="val => dialogOpen = val" @saved="handleSaved" />
    </div>
  </div>
</template>
