import { defineStore } from 'pinia'
import { api } from '@/lib/api'
import type { Settings } from '@/types/api'
import { useToast } from '@/composables/use-toast'

interface SettingsState {
  settings: Settings | null
  loading: boolean
  error: string | null
}

export const useSettingsStore = defineStore('settings', {
  state: (): SettingsState => ({
    settings: null,
    loading: false,
    error: null,
  }),

  actions: {
    async fetchSettings() {
      this.loading = true
      this.error = null
      try {
        this.settings = await api.get<Settings>('/settings')
      } catch (error) {
        this.error = 'Failed to fetch settings'
        console.error(error)
      } finally {
        this.loading = false
      }
    },

    async updateSettings(newSettings: Partial<Settings>) {
      if (!this.settings) return

      const { toast } = useToast()
      this.loading = true
      this.error = null
      try {
        const updatedSettings = { ...this.settings, ...newSettings }
        this.settings = await api.put<Settings>('/settings', updatedSettings)
        
        // Apply theme immediately
        if (newSettings.theme) {
          document.documentElement.classList.toggle('dark', newSettings.theme === 'dark')
          localStorage.setItem('theme', newSettings.theme)
        }

        toast({
          title: 'Settings Updated',
          description: 'Your changes have been saved successfully.',
        })
      } catch (error) {
        this.error = 'Failed to update settings'
        console.error(error)
        toast({
          title: 'Error',
          description: 'Failed to save your settings. Please try again.',
          variant: 'destructive',
        })
      } finally {
        this.loading = false
      }
    },
  },
})
