<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  LayoutDashboard,
  Inbox,
  FlaskConical,
  ChevronRight,
  Settings,
  Activity,
  Sparkles,
  Brain,
  Swords,
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

const route = useRoute()
// Ensure only the root path (`/`) matches exactly, while other paths use `startsWith`.
const isActive = (path: string) => {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}
</script>

<template>
  <aside class="w-72 flex-shrink-0 border-r border-border bg-sidebar flex flex-col h-screen">
    <!-- Logo Section -->
    <div class="p-6 pb-2">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Brain class="w-6 h-6 text-primary" />
        </div>
        <div>
          <h1 class="text-xl font-semibold tracking-tight">MindEcho</h1>
          <p class="text-xs text-muted-foreground">思维回响</p>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 px-4 py-4 space-y-1">
      <NuxtLink 
        to="/"
        :class="[
          'group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200',
          isActive('/') 
            ? 'bg-primary/10 text-primary shadow-sm' 
            : 'hover:bg-accent hover:text-accent-foreground'
        ]"
      >
        <LayoutDashboard :class="[
          'mr-3 h-5 w-5 transition-transform duration-200',
          isActive('/') ? 'scale-110' : 'group-hover:scale-110'
        ]" />
        <span>仪表盘</span>
        <div v-if="isActive('/')" class="ml-auto w-1.5 h-5 bg-primary rounded-full" />
      </NuxtLink>

      <NuxtLink 
        to="/inbox"
        :class="[
          'group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200',
          isActive('/inbox') 
            ? 'bg-primary/10 text-primary shadow-sm' 
            : 'hover:bg-accent hover:text-accent-foreground'
        ]"
      >
        <Inbox :class="[
          'mr-3 h-5 w-5 transition-transform duration-200',
          isActive('/inbox') ? 'scale-110' : 'group-hover:scale-110'
        ]" />
        <span>收件箱</span>
        <span class="ml-auto text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
          12
        </span>
      </NuxtLink>

      <NuxtLink 
        to="/collections"
        :class="[
          'group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200',
          isActive('/collections') 
            ? 'bg-primary/10 text-primary shadow-sm' 
            : 'hover:bg-accent hover:text-accent-foreground'
        ]"
      >
        <LayoutDashboard :class="[
          'mr-3 h-5 w-5 transition-transform duration-200',
          isActive('/collections') ? 'scale-110' : 'group-hover:scale-110'
        ]" />
        <span>全部收藏</span>
        <div v-if="isActive('/collections')" class="ml-auto w-1.5 h-5 bg-primary rounded-full" />
      </NuxtLink>

      <NuxtLink 
        to="/workshops"
        :class="[
          'group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200',
          isActive('/workshops') 
            ? 'bg-primary/10 text-primary shadow-sm' 
            : 'hover:bg-accent hover:text-accent-foreground'
        ]"
      >
        <Sparkles :class="[
          'mr-3 h-5 w-5 transition-transform duration-200',
          isActive('/workshops') ? 'scale-110' : 'group-hover:scale-110'
        ]" />
        <span>AI 工坊</span>
        <div v-if="isActive('/workshops')" class="ml-auto w-1.5 h-5 bg-primary rounded-full" />
      </NuxtLink>
    </nav>

    <!-- Footer -->
    <div class="p-4 border-t border-border space-y-3">
      <!-- Sync Status -->
      <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50">
        <div class="relative">
          <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <div class="absolute inset-0 w-2 h-2 bg-green-500 rounded-full animate-ping" />
        </div>
        <span class="text-xs text-muted-foreground">已同步最新数据</span>
      </div>

      <!-- Settings Button -->
      <NuxtLink
        to="/settings"
        class="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium hover:bg-accent hover:text-accent-foreground"
      >
        <Settings class="mr-2 h-4 w-4" />
        设置
      </NuxtLink>
    </div>
  </aside>
</template>

<style scoped>
/* Subtle gradient for active state */
.bg-primary\/10 {
  background-image: linear-gradient(
    to right,
    oklch(from var(--primary) l c h / 0.1),
    oklch(from var(--primary) l c h / 0.05)
  );
}
</style>