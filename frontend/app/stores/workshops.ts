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
}

export const useWorkshopsStore = defineStore('workshops', {
  state: (): WorkshopsState => ({
    workshops: [],
    tasks: {},
    loading: false,
    error: null,
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

    async fetchWorkshopBySlug(slug: string) {
      this.loading = true
      this.error = null
      try {
        const wk = await api.get<Workshop>(`/workshops/manage/${slug}`)
        const idx = (this.workshops as any[]).findIndex((w: any) => w.workshop_id === slug)
        if (idx >= 0) {
          this.workshops[idx] = wk
        } else {
          this.workshops.push(wk)
        }
        return wk
      } catch (error) {
        this.error = 'Failed to fetch workshop'
        console.error(error)
        return null
      } finally {
        this.loading = false
      }
    },

    async executeWorkshop(
      workshopIdOrSlug: string,
      collectionId?: number,
      extraPayload?: Record<string, any>
    ): Promise<string | null> {
      this.loading = true
      this.error = null
      const { toast } = useToast()
      try {
        const body: Record<string, any> = { ...(extraPayload || {}) }
        if (typeof collectionId === 'number' && collectionId >= 0) {
          body.collection_id = collectionId
        }
        const response = await api.post<{ task_id: string }>(`/workshops/${workshopIdOrSlug}/execute`, body)
        const taskId = response.task_id
        
        // Immediately fetch the initial task state
        await this.fetchTask(taskId)

        toast({
          title: `Workshop "${workshopIdOrSlug}" Started`,
          description: `Task has been successfully dispatched.`,
        })

        return taskId
      } catch (error) {
        this.error = 'Failed to execute workshop'
        console.error(error)
        toast({
          title: 'Execution Error',
          description: 'Failed to start the workshop. Please try again.',
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

    // Replaced websocket streaming with polling
    subscribeToTask(taskId: string) {
      const interval = setInterval(async () => {
        await this.fetchTask(taskId)
        const task = this.tasks[taskId]
        if (!task) return
        if (task.status === 'success' || task.status === 'failure') {
          clearInterval(interval)
        }
      }, 2000)
      return () => clearInterval(interval)
    },

    subscribeToTaskStarts(onStart?: (taskId: string) => void) {
      // Poll recent tasks to discover new ones
      const seen = new Set<string>()
      const interval = setInterval(async () => {
        try {
          const res = await api.get<{ total: number; items: Task[] }>(`/tasks?page=1&size=20`)
          for (const t of res.items) {
            if (!seen.has(String(t.id))) {
              seen.add(String(t.id))
              this.tasks[String(t.id)] = t
              if (onStart) onStart(String(t.id))
            }
          }
        } catch (e) {
          console.error('Poll tasks error', e)
        }
      }, 5000)
      return () => clearInterval(interval)
    },

    // ---------- CRUD ----------
    async createWorkshop(payload: Partial<Workshop>) {
      try {
        const newWorkshop = await api.post<Workshop>('/workshops/manage', payload)
        this.workshops.push(newWorkshop)
        return newWorkshop
      } catch (err) {
        this.error = 'Failed to create workshop'
        throw err
      }
    },

    async updateWorkshop(workshopId: string, payload: Partial<Workshop>) {
      try {
        const updated = await api.put<Workshop>(`/workshops/manage/${workshopId}`, payload)
        const idx = this.workshops.findIndex(w => (w as any).workshop_id === workshopId || (w as any).id === workshopId)
        if (idx >= 0) this.workshops[idx] = updated
        return updated
      } catch (err) {
        this.error = 'Failed to update workshop'
        throw err
      }
    },

    async toggleListening(workshopId: string, enabled: boolean, workshopName?: string) {
      try {
        await api.post(`/workshops/manage/${workshopId}/toggle-listening`, { enabled, workshop_name: workshopName ?? undefined })
        // Refresh single workshop to get updated executor_config
        const wk = await api.get<Workshop>(`/workshops/manage/${workshopId}`)
        const idx = (this.workshops as any[]).findIndex((w: any) => w.workshop_id === workshopId)
        if (idx >= 0) this.workshops[idx] = wk
        else this.workshops.push(wk)
      } catch (err) {
        this.error = 'Failed to toggle listening'
        throw err
      }
    },

    async deleteWorkshop(workshopId: string) {
      try {
        await api.delete(`/workshops/manage/${workshopId}`)
        this.workshops = this.workshops.filter(w => (w as any).workshop_id !== workshopId && (w as any).id !== workshopId)
      } catch (err) {
        this.error = 'Failed to delete workshop'
        throw err
      }
    },

    // ---------- Platform Bindings ----------
    async getPlatformBindings(workshopId: string) {
      try {
        const response = await api.get<{
          platform_bindings: Array<{ platform: string; collection_ids: number[] }>
          listening_enabled: boolean
        }>(`/workshops/manage/${workshopId}/platform-bindings`)
        return response
      } catch (err) {
        this.error = 'Failed to get platform bindings'
        throw err
      }
    },

    async updatePlatformBindings(workshopId: string, bindings: Array<{ platform: string; collection_ids: number[] }>) {
      try {
        const response = await api.put<{
          ok: boolean
          platform_bindings: Array<{ platform: string; collection_ids: number[] }>
        }>(`/workshops/manage/${workshopId}/platform-bindings`, {
          platform_bindings: bindings
        })

        // Refresh workshop to get updated config
        await this.fetchWorkshopBySlug(workshopId)

        return response
      } catch (err) {
        this.error = 'Failed to update platform bindings'
        throw err
      }
    },

    // ---------- Helpers ----------
    getWorkshopById(id: string) {
      return (this.workshops as any[]).find((w: any) => String(w.id) === String(id))
    },

    getWorkshopBySlug(slug: string) {
      // align with backend which returns `workshop_id` as slug
      return this.workshops.find((w: any) => w.workshop_id === slug)
    },

  },
})
