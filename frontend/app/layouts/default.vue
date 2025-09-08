<script setup lang="ts">
import LayoutSidebar from '@/components/layout/Sidebar.vue'
import LayoutCommandPalette from '@/components/layout/CommandPalette.vue'
</script>

<template>
  <div class="flex h-screen bg-background text-foreground">
    <LayoutSidebar />
    <main class="flex-1 overflow-y-auto relative">
      <div class="container mx-auto p-8 relative z-10">
        <slot />
      </div>
      <LayoutCommandPalette />
    </main>
  </div>
</template>
