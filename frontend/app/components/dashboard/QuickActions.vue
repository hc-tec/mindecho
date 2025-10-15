<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card'
import { Button } from '~/components/ui/button'
import { Zap, PlusCircle, Play, Square } from 'lucide-vue-next'
import { api } from '@/lib/api'
import { ref } from 'vue'

const starting = ref(false)
const stopping = ref(false)

const startWatcher = async () => {
  starting.value = true
  try {
    await api.post('/streams/start?plugin_id=favorites_watcher&group=favorites-updates&run_mode=recurring&interval=120&buffer_size=200')
  } finally {
    starting.value = false
  }
}

const stopWatcher = async () => {
  stopping.value = true
  try {
    await api.post('/streams/favorites-updates/stop')
  } finally {
    stopping.value = false
  }
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>Quick Actions</CardTitle>
    </CardHeader>
    <CardContent class="flex flex-col space-y-2">
      <div class="grid grid-cols-2 gap-2">
        <Button :disabled="starting" @click="startWatcher">
          <Play class="mr-2 h-4 w-4" />
          启动收藏监听
        </Button>
        <Button variant="secondary" :disabled="stopping" @click="stopWatcher">
          <Square class="mr-2 h-4 w-4" />
          停止收藏监听
        </Button>
      </div>
      <Button variant="ghost">
        <Zap class="mr-2 h-4 w-4" />
        立即同步所有平台
      </Button>
      <Button variant="secondary">
        <PlusCircle class="mr-2 h-4 w-4" />
        创建一份空白笔记
      </Button>
    </CardContent>
  </Card>
</template>
