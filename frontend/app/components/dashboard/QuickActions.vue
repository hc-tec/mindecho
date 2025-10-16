<script setup lang="ts">
/**
 * 快捷操作组件
 *
 * 提供常用的快捷操作按钮：
 * - 启动/停止收藏监听
 * - 立即同步所有平台
 * - 创建新笔记（预留功能）
 *
 * 设计特点：
 * - 简洁的按钮布局
 * - 加载状态反馈
 * - 关键操作突出显示
 */

import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card'
import { Button } from '~/components/ui/button'
import { Zap, PlusCircle, Play, Square } from 'lucide-vue-next'
import { api } from '@/lib/api'
import { ref } from 'vue'
import { useToast } from '@/composables/use-toast'

// ============================================================================
// 状态管理
// ============================================================================

/**
 * 启动监听的加载状态
 */
const starting = ref(false)

/**
 * 停止监听的加载状态
 */
const stopping = ref(false)

const { toast } = useToast()

// ============================================================================
// 操作函数
// ============================================================================

/**
 * 启动收藏监听
 *
 * 调用后端 API 启动流式监听器
 * 监听器会每120秒检查一次收藏更新
 */
const startWatcher = async () => {
  starting.value = true
  try {
    await api.post('/streams/start', {
      plugin_id: 'favorites_watcher',
      group: 'favorites-updates',
      run_mode: 'recurring',
      interval: 120,
      buffer_size: 200
    })
    toast({
      title: '监听已启动',
      description: '收藏监听器已开始运行'
    })
  } catch (error) {
    console.error('Failed to start watcher:', error)
    toast({
      title: '启动失败',
      description: '无法启动收藏监听器',
      variant: 'destructive'
    })
  } finally {
    starting.value = false
  }
}

/**
 * 停止收藏监听
 *
 * 调用后端 API 停止流式监听器
 */
const stopWatcher = async () => {
  stopping.value = true
  try {
    await api.post('/streams/favorites-updates/stop')
    toast({
      title: '监听已停止',
      description: '收藏监听器已停止运行'
    })
  } catch (error) {
    console.error('Failed to stop watcher:', error)
    toast({
      title: '停止失败',
      description: '无法停止收藏监听器',
      variant: 'destructive'
    })
  } finally {
    stopping.value = false
  }
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="text-lg">快捷操作</CardTitle>
    </CardHeader>

    <CardContent class="flex flex-col space-y-2">
      <!-- 监听控制按钮（2列网格） -->
      <div class="grid grid-cols-2 gap-2">
        <Button
          :disabled="starting"
          @click="startWatcher"
          class="flex items-center justify-center"
        >
          <Play class="mr-2 h-4 w-4" />
          启动监听
        </Button>

        <Button
          variant="secondary"
          :disabled="stopping"
          @click="stopWatcher"
          class="flex items-center justify-center"
        >
          <Square class="mr-2 h-4 w-4" />
          停止监听
        </Button>
      </div>

      <!-- 其他快捷操作 -->
      <Button variant="ghost" class="w-full justify-start">
        <Zap class="mr-2 h-4 w-4" />
        立即同步所有平台
      </Button>

      <Button variant="ghost" class="w-full justify-start">
        <PlusCircle class="mr-2 h-4 w-4" />
        创建一份空白笔记
      </Button>
    </CardContent>
  </Card>
</template>
