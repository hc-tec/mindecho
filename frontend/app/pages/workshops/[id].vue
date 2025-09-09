<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { useWorkshopsStore } from '@/stores/workshops'

const route = useRoute()
const workshopsStore = useWorkshopsStore()

const workshopId = computed(() => String(route.params.id))

const workshop = computed(() => workshopsStore.getWorkshopById(workshopId.value))

// 动态组件按类型加载
const DynamicComponent = computed(() => {
  if (!workshop.value) return null
  const loader = workshopsStore.getComponentLoader(workshop.value.type)
  return defineAsyncComponent(loader)
})
</script>

<template>
  <div v-if="!workshop">加载中...</div>
  <component v-else :is="DynamicComponent" :workshop="workshop" />
</template>
