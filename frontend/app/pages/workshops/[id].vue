<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useWorkshopsStore } from '@/stores/workshops'

const route = useRoute()
const workshopsStore = useWorkshopsStore()

// route param is slug (workshop_id)
const workshopSlug = computed(() => String(route.params.id))

// try to get by slug; fallback to id for backward compatibility
const workshop = computed(() => {
  const bySlug = workshopsStore.getWorkshopBySlug?.(workshopSlug.value)
  if (bySlug) return bySlug
  return workshopsStore.getWorkshopById?.(workshopSlug.value)
})

onMounted(async () => {
  if (!workshop.value && !workshopsStore.loading) {
    await workshopsStore.fetchWorkshops()
  }
})

// 动态组件按类型加载
const DynamicComponent = computed(() => {
  if (!workshop.value) return null
  const key = workshop.value.workshop_id || workshop.value.type
  const loader = workshopsStore.getComponentLoader(key)
  return defineAsyncComponent(loader)
})
</script>

<template>
  <div v-if="!workshop">加载中...</div>
  <component v-else :is="DynamicComponent" :workshop="workshop" />
</template>
