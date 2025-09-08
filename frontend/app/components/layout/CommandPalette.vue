<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import {
  Dialog,
  DialogContent,
} from '~/components/ui/dialog'
import { Command } from 'vue-command-palette'
import {
  LayoutDashboard,
  Inbox,
  FlaskConical,
  Settings,
  Search,
} from 'lucide-vue-next'

const open = ref(false)

onMounted(() => {
  const onKeyDown = (e: KeyboardEvent) => {
    if ((e.key === 'k' && (e.metaKey || e.ctrlKey))) {
      e.preventDefault()
      open.value = !open.value
    }
  }
  document.addEventListener('keydown', onKeyDown)
  onUnmounted(() => {
    document.removeEventListener('keydown', onKeyDown)
  })
})
</script>

<template>
  <Dialog :open="open" @update:open="open = $event">
    <DialogContent class="overflow-hidden p-0 shadow-lg">
      <Command class="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-group]]:px-2 [&_[cmdk-input-wrapper]_svg]:h-5 [&_[cmdk-input-wrapper]_svg]:w-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5">
        <Command.Input placeholder="Type a command or search..." />
        <Command.List>
          <Command.Empty>No results found.</Command.Empty>
          <Command.Group heading="Navigation">
            <Command.Item value="dashboard">
              <LayoutDashboard class="mr-2 h-4 w-4" />
              <span>Dashboard</span>
            </Command.Item>
            <Command.Item value="inbox">
              <Inbox class="mr-2 h-4 w-4" />
              <span>Inbox</span>
            </Command.Item>
            <Command.Item value="settings">
              <Settings class="mr-2 h-4 w-4" />
              <span>Settings</span>
            </Command.Item>
          </Command.Group>
          <Command.Separator />
          <Command.Group heading="AI Workshops">
            <Command.Item value="snapshot-insight">
              <FlaskConical class="mr-2 h-4 w-4" />
              <span>Snapshot Insight</span>
            </Command.Item>
            <Command.Item value="information-alchemy">
              <FlaskConical class="mr-2 h-4 w-4" />
              <span>Information Alchemy</span>
            </Command.Item>
            <Command.Item value="point-counterpoint">
              <FlaskConical class="mr-2 h-4 w-4" />
              <span>Point Counterpoint</span>
            </Command.Item>
          </Command.Group>
          <Command.Separator />
          <Command.Group heading="Actions">
            <Command.Item value="search">
              <Search class="mr-2 h-4 w-4" />
              <span>Search all collections...</span>
            </Command.Item>
          </Command.Group>
        </Command.List>
      </Command>
    </DialogContent>
  </Dialog>
</template>
