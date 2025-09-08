<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useWorkshopsStore } from '@/stores/workshops'
import type { Workshop } from '@/types/api'

// Dynamically import workshop components.
// NOTE: For a real-world app with many components, async components (`defineAsyncComponent`) would be better for code-splitting.
import InformationAlchemy from '@/components/workshops/InformationAlchemy.vue'
import PointCounterpoint from '@/components/workshops/PointCounterpoint.vue'
import FallbackWorkshop from '@/components/workshops/FallbackWorkshop.vue'

const route = useRoute()
const store = useWorkshopsStore()

const workshopId = computed(() => route.params.id as string)
const workshop = computed<Workshop | undefined>(() => 
  store.workshops.find(w => w.workshop_id === workshopId.value)
)

onMounted(() => {
  // If the user navigates directly to this page, the workshops might not be loaded yet.
  if (store.workshops.length === 0) {
    store.fetchWorkshops()
  }
})

// This component map is the core of the router.
// It links a string ID from the database to a specific Vue component.
const workshopComponentMap: { [key: string]: any } = {
  'information-alchemy': InformationAlchemy,
  'point-counterpoint': PointCounterpoint,
  // 'snapshot-insight': SomeComponent, // Example for the future
}

const activeWorkshopComponent = computed(() => {
  if (!workshop.value) {
    // Return fallback if workshop data isn't found, even after loading.
    return FallbackWorkshop
  }
  // Return the mapped component, or the fallback if no component is mapped to the ID.
  return workshopComponentMap[workshop.value.workshop_id] || FallbackWorkshop
})
</script>

<template>
  <div class="h-full flex flex-col">
    <div v-if="store.loading && !workshop" class="flex items-center justify-center h-full">
      <p class="text-muted-foreground">Loading workshop data...</p>
    </div>
    
    <component 
      v-else 
      :is="activeWorkshopComponent" 
      :workshop-info="workshop" 
    />
  </div>
</template>
