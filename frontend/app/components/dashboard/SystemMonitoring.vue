<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import { Activity, Loader2, Lock, Unlock, AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-vue-next'

interface ExecutorStatus {
  executor_type: string
  concurrency_limit: number | null
  description: string
  is_unlimited: boolean
}

interface TaskQueueStats {
  pending: number
  in_progress: number
  success: number
  failed: number
  total: number
}

interface RecoveryStats {
  items_need_details: number
  items_need_tasks: number
  total_incomplete: number
}

interface MonitoringData {
  executors: ExecutorStatus[]
  task_queue: TaskQueueStats
  recovery_stats: RecoveryStats
}

const monitoringData = ref<MonitoringData | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const fetchMonitoringData = async () => {
  try {
    loading.value = true
    error.value = null
    const data = await api.get<MonitoringData>('/dashboard/monitoring')
    monitoringData.value = data
  } catch (err: any) {
    error.value = err.message || 'Failed to load monitoring data'
    console.error('Failed to fetch monitoring data:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchMonitoringData()
  // Refresh every 30 seconds
  const interval = setInterval(fetchMonitoringData, 30000)
  // Cleanup on unmount
  return () => clearInterval(interval)
})

const taskQueuePercentages = computed(() => {
  if (!monitoringData.value?.task_queue.total) return null
  const { pending, in_progress, success, failed, total } = monitoringData.value.task_queue
  return {
    pending: ((pending / total) * 100).toFixed(1),
    in_progress: ((in_progress / total) * 100).toFixed(1),
    success: ((success / total) * 100).toFixed(1),
    failed: ((failed / total) * 100).toFixed(1)
  }
})
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex items-center justify-between">
        <div>
          <CardTitle class="flex items-center gap-2">
            <Activity class="h-5 w-5" />
            系统监控
          </CardTitle>
          <CardDescription>实时系统状态与执行器监控</CardDescription>
        </div>
        <Badge variant="outline" class="flex items-center gap-1">
          <div class="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
          实时
        </Badge>
      </div>
    </CardHeader>
    <CardContent>
      <!-- Loading State -->
      <div v-if="loading && !monitoringData" class="flex items-center justify-center py-12">
        <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" />
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="flex items-center justify-center py-12 text-destructive">
        <AlertCircle class="h-5 w-5 mr-2" />
        {{ error }}
      </div>

      <!-- Content -->
      <div v-else-if="monitoringData" class="space-y-6">
        <!-- Executor Status -->
        <div>
          <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
            <Lock class="h-4 w-4" />
            执行器并发控制
          </h3>
          <div class="space-y-2">
            <div
              v-for="executor in monitoringData.executors"
              :key="executor.executor_type"
              class="flex items-center justify-between p-3 rounded-lg border bg-card"
            >
              <div class="flex items-center gap-3">
                <component
                  :is="executor.is_unlimited ? Unlock : Lock"
                  :class="[
                    'h-4 w-4',
                    executor.is_unlimited ? 'text-green-500' : 'text-amber-500'
                  ]"
                />
                <div>
                  <div class="text-sm font-medium">{{ executor.executor_type }}</div>
                  <div class="text-xs text-muted-foreground">{{ executor.description }}</div>
                </div>
              </div>
              <Badge :variant="executor.is_unlimited ? 'outline' : 'secondary'">
                {{ executor.is_unlimited ? '无限制' : `限制: ${executor.concurrency_limit}` }}
              </Badge>
            </div>
          </div>
        </div>

        <!-- Task Queue Stats -->
        <div>
          <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
            <Activity class="h-4 w-4" />
            任务队列 (总计: {{ monitoringData.task_queue.total }})
          </h3>
          <div class="grid grid-cols-2 gap-3">
            <div class="p-3 rounded-lg border bg-blue-500/10 border-blue-500/20">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock class="h-3 w-3" />
                  等待中
                </span>
                <span class="text-lg font-bold text-blue-500">
                  {{ monitoringData.task_queue.pending }}
                </span>
              </div>
              <div v-if="taskQueuePercentages" class="text-xs text-muted-foreground">
                {{ taskQueuePercentages.pending }}%
              </div>
            </div>

            <div class="p-3 rounded-lg border bg-amber-500/10 border-amber-500/20">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-muted-foreground flex items-center gap-1">
                  <Loader2 class="h-3 w-3" />
                  执行中
                </span>
                <span class="text-lg font-bold text-amber-500">
                  {{ monitoringData.task_queue.in_progress }}
                </span>
              </div>
              <div v-if="taskQueuePercentages" class="text-xs text-muted-foreground">
                {{ taskQueuePercentages.in_progress }}%
              </div>
            </div>

            <div class="p-3 rounded-lg border bg-green-500/10 border-green-500/20">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-muted-foreground flex items-center gap-1">
                  <CheckCircle class="h-3 w-3" />
                  已完成
                </span>
                <span class="text-lg font-bold text-green-500">
                  {{ monitoringData.task_queue.success }}
                </span>
              </div>
              <div v-if="taskQueuePercentages" class="text-xs text-muted-foreground">
                {{ taskQueuePercentages.success }}%
              </div>
            </div>

            <div class="p-3 rounded-lg border bg-red-500/10 border-red-500/20">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-muted-foreground flex items-center gap-1">
                  <XCircle class="h-3 w-3" />
                  失败
                </span>
                <span class="text-lg font-bold text-red-500">
                  {{ monitoringData.task_queue.failed }}
                </span>
              </div>
              <div v-if="taskQueuePercentages" class="text-xs text-muted-foreground">
                {{ taskQueuePercentages.failed }}%
              </div>
            </div>
          </div>
        </div>

        <!-- Recovery Stats -->
        <div>
          <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
            <AlertCircle class="h-4 w-4" />
            恢复统计
          </h3>
          <div class="space-y-2">
            <div class="p-3 rounded-lg border bg-card">
              <div class="flex items-center justify-between">
                <span class="text-sm">缺少详情的内容</span>
                <Badge variant="outline">
                  {{ monitoringData.recovery_stats.items_need_details }}
                </Badge>
              </div>
            </div>
            <div class="p-3 rounded-lg border bg-card">
              <div class="flex items-center justify-between">
                <span class="text-sm">缺少任务的内容</span>
                <Badge variant="outline">
                  {{ monitoringData.recovery_stats.items_need_tasks }}
                </Badge>
              </div>
            </div>
            <div class="p-3 rounded-lg border bg-amber-500/10 border-amber-500/20">
              <div class="flex items-center justify-between">
                <span class="text-sm font-semibold">总计待恢复</span>
                <Badge variant="secondary" class="bg-amber-500/20 text-amber-700 dark:text-amber-300">
                  {{ monitoringData.recovery_stats.total_incomplete }}
                </Badge>
              </div>
            </div>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>
