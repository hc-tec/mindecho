import { defineStore } from 'pinia'
import { api } from '@/lib/api'
import type { Workshop, Task, FavoriteItem } from '@/types/api'
import { useWebSocket } from '@/composables/useWebSocket'
import { useToast } from '@/composables/use-toast'

interface WorkshopsState {
  workshops: Workshop[]
  tasks: Record<string, Task>
  loading: boolean
  error: string | null
  /** 动态组件加载器映射 */
  componentMap: Record<string, () => Promise<any>>
}

export const useWorkshopsStore = defineStore('workshops', {
  state: (): WorkshopsState => ({
    workshops: [],
    tasks: {},
    loading: false,
    error: null,
    // 动态组件映射 (type -> component name)，在 setup 中通过 import.meta.glob 可进一步自动注册
    // 这里先手动内置常见映射，未知类型 fallback 到 GenericWorkshop
    componentMap: {
      'information-alchemy': () => import('@/components/workshops/InformationAlchemy.vue'),
      'point-counterpoint': () => import('@/components/workshops/PointCounterpoint.vue'),
      'generic': () => import('@/components/workshops/GenericWorkshop.vue'),
    } as Record<string, () => Promise<any>>,
  }),

  actions: {
    async fetchWorkshops() {
      this.loading = true
      this.error = null
      try {
        this.workshops = await api.get<Workshop[]>('/workshops/manage')
      } catch (error) {
        this.error = 'Failed to fetch workshops'
        console.error(error)
      } finally {
        this.loading = false
      }
    },

    async executeWorkshop(
      workshopId: string,
      itemId?: number,
      extraPayload?: Record<string, any>
    ): Promise<string | null> {
      this.loading = true
      this.error = null
      const { toast } = useToast()
      try {
        const body: Record<string, any> = { ...(extraPayload || {}) }
        if (typeof itemId === 'number' && itemId >= 0) {
          body.favorite_item_id = itemId
        }
        const response = await api.post<{ task_id: string }>(`/workshops/${workshopId}/execute`, body)
        const taskId = response.task_id
        
        // Immediately fetch the initial task state
        await this.fetchTask(taskId)

        toast({
          title: `Workshop "${workshopId}" Started`,
          description: `Task has been successfully dispatched.`,
        })

        return taskId
      } catch (error) {
        this.error = 'Failed to execute workshop'
        console.error(error)
        toast({
          title: 'Execution Error',
          description: 'Failed to start the workshop. Please try again.',
          variant: 'destructive',
        })
        return null
      } finally {
        this.loading = false
      }
    },

    async fetchTask(taskId: string) {
      try {
        const task = await api.get<Task>(`/tasks/${taskId}`)
        this.tasks[taskId] = task
      } catch (error) {
        console.error(`Failed to fetch task ${taskId}`, error)
      }
    },

    subscribeToTask(taskId: string) {
      const wsUrl = `ws://127.0.0.1:8001/api/v1/workshops/ws/${taskId}`
      const { onMessage, disconnect } = useWebSocket(wsUrl)

      const unsubscribe = onMessage((data) => {
        // Update task state based on WebSocket messages
        const task = this.tasks[taskId]
        if (!task) return

        if (data.status) {
          task.status = data.status
        }
        if (data.type === 'token' && data.data) {
          if (!task.result) {
            task.result = { content: '' } // Initialize if it doesn't exist
          }
          task.result.content += data.data
        }
        if (data.status === 'success' || data.status === 'failure') {
          if (data.result) {
            task.result = { content: data.result }
          }
          if(data.error) {
            task.error = data.error
          }
          task.completed_at = new Date().toISOString()
          unsubscribe()
          disconnect()
        }
      })
      
      return unsubscribe
    },

    // ---------- CRUD ----------
    async createWorkshop(payload: Partial<Workshop>) {
      try {
        const newWorkshop = await api.post<Workshop>('/workshops', payload)
        this.workshops.push(newWorkshop)
        return newWorkshop
      } catch (err) {
        this.error = 'Failed to create workshop'
        throw err
      }
    },

    async updateWorkshop(id: string, payload: Partial<Workshop>) {
      try {
        const updated = await api.put<Workshop>(`/workshops/${id}`, payload)
        const idx = this.workshops.findIndex(w => w.id === id)
        if (idx >= 0) this.workshops[idx] = updated
        return updated
      } catch (err) {
        this.error = 'Failed to update workshop'
        throw err
      }
    },

    async deleteWorkshop(id: string) {
      try {
        await api.delete(`/workshops/${id}`)
        this.workshops = this.workshops.filter(w => w.id !== id)
      } catch (err) {
        this.error = 'Failed to delete workshop'
        throw err
      }
    },

    // ---------- Helpers ----------
    getWorkshopById(id: string) {
      return this.workshops.find(w => w.id === id)
    },

    getComponentLoader(type: string) {
      return this.componentMap[type] ?? this.componentMap['generic']
    },
  },
})
