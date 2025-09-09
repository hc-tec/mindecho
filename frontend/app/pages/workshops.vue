<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useWorkshopsStore } from '@/stores/workshops'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '@/components/ui/dropdown-menu'
import WorkshopConfigForm from '@/components/workshops/WorkshopConfigForm.vue'
import { useRouter } from 'vue-router'
import { Badge } from '@/components/ui/badge'

const store = useWorkshopsStore()
const router = useRouter()

onMounted(() => {
  store.fetchWorkshops()
})

const workshops = computed(() => store.workshops)
const isLoading = computed(() => store.loading)

// dialog state
const dialogOpen = ref(false)
const editingWorkshop = ref(null as any)

const openCreate = () => {
  editingWorkshop.value = null
  dialogOpen.value = true
}

const openEdit = (wk) => {
  editingWorkshop.value = wk
  dialogOpen.value = true
}

const handleSaved = () => {
  store.fetchWorkshops()
}

const handleDelete = async (wk) => {
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
    <header class="p-4 border-b border-border bg-muted/50">
      <h2 class="text-2xl font-bold tracking-tight">AI 工作坊</h2>
      <p class="text-muted-foreground">选择一个工作坊来处理您的收藏或输入。</p>
    </header>

    <div class="flex-1 overflow-y-auto p-8">
      <div v-if="isLoading" class="text-center text-muted-foreground">
        <p>正在加载工作坊...</p>
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card 
          v-for="workshop in workshops" 
          :key="workshop.workshop_id || workshop.id" 
          class="flex flex-col hover:shadow-lg transition-shadow relative"
        >
          <!-- kebab menu -->
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" size="icon" class="absolute top-2 right-2">
                <span class="sr-only">菜单</span>
                ···
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem @click="openEdit(workshop)">编辑</DropdownMenuItem>
              <DropdownMenuItem class="text-destructive" @click="handleDelete(workshop)">删除</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <CardHeader>
            <CardTitle>{{ workshop.name }}</CardTitle>
            <CardDescription class="line-clamp-3 h-[60px]">{{ workshop.description }}</CardDescription>
            <div class="mt-2 flex items-center gap-2">
              <Badge variant="outline" v-if="workshop.executor_type">{{ workshop.executor_type }}</Badge>
              <Badge v-if="workshop.default_model">{{ workshop.default_model }}</Badge>
            </div>
          </CardHeader>
          <CardContent class="flex-1 flex items-end">
            <Button @click="goToWorkshop(workshop.workshop_id || workshop.id)" class="w-full">
              进入工作坊
            </Button>
          </CardContent>
        </Card>
      </div>
      <!-- 新建工坊按钮 -->
      <div class="fixed bottom-8 right-8">
        <Button variant="secondary" size="lg" @click="openCreate">
          新建工坊
        </Button>
      </div>

      <WorkshopConfigForm :open="dialogOpen" :workshop="editingWorkshop" @update:open="val => dialogOpen = val" @saved="handleSaved" />
    </div>
  </div>
</template>
