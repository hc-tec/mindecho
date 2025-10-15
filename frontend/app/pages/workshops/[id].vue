<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useWorkshopsStore } from '@/stores/workshops'
import InformationAlchemy from '@/components/workshops/InformationAlchemy.vue'
import PointCounterpoint from '@/components/workshops/PointCounterpoint.vue'
import GenericWorkshop from '@/components/workshops/GenericWorkshop.vue'

// definePageMeta({ path: '/workshops/:id' })

const route = useRoute()
const workshopsStore = useWorkshopsStore()

// route param is slug (workshop_id)
const workshopSlug = route.params.id

console.log(workshopSlug);

// try to get by slug; fallback to id for backward compatibility
const workshop = computed(() => {
  const bySlug = workshopsStore.getWorkshopBySlug?.(workshopSlug)
  if (bySlug) return bySlug
  return workshopsStore.getWorkshopById?.(workshopSlug)
})


onMounted(async () => {
  if (!workshop.value && !workshopsStore.loading) {
    // Try fetching a single workshop by slug first; fallback to full list
    const single = await (workshopsStore as any).fetchWorkshopBySlug?.(workshopSlug)
    if (!single) {
      await workshopsStore.fetchWorkshops()
    }
  }
})

// 静态组件选择逻辑
const componentKey = computed(() => (workshop.value as any)?.workshop_id || (workshop.value as any)?.type || 'generic')
</script>

<template>
  
  <div v-if="!workshop && workshopsStore.loading">加载中...</div>
  <div v-else-if="!workshop && !workshopsStore.loading" class="p-8 text-center text-muted-foreground">未找到该工作坊。</div>
  <template v-else>
    <InformationAlchemy v-if="componentKey === 'information-alchemy'" :workshop="workshop" />
    <PointCounterpoint v-else-if="componentKey === 'point-counterpoint'" :workshop="workshop" />
    <GenericWorkshop v-else :workshop="workshop" />
  </template>
  
</template>
