// API client configuration
export const API_BASE_URL = 'http://127.0.0.1:8001/api/v1'

interface ApiRequestOptions extends RequestInit {
  params?: Record<string, any>
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async request<T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T> {
    const { params, ...fetchOptions } = options
    
    let url = `${this.baseUrl}${endpoint}`
    
    if (params) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value))
        }
      })
      const queryString = searchParams.toString()
      if (queryString) {
        url += `?${queryString}`
      }
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', params })
  }

  async post<T>(endpoint: string, data?: any, params?: Record<string, any>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      params,
    })
  }

  async put<T>(endpoint: string, data?: any, params?: Record<string, any>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
      params,
    })
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

export const api = new ApiClient(API_BASE_URL)

// ============================================================================
// Notification Config API
// ============================================================================

import type { NotificationConfig, NotificationConfigCreate, NotificationConfigUpdate } from '@/types/api'

/**
 * Get all notification configs
 */
export const getNotificationConfigs = async (): Promise<NotificationConfig[]> => {
  return api.get<NotificationConfig[]>('/notification-configs')
}

/**
 * Get notification config for a specific workshop
 */
export const getNotificationConfig = async (workshopId: string): Promise<NotificationConfig> => {
  return api.get<NotificationConfig>(`/notification-configs/${workshopId}`)
}

/**
 * Create notification config
 */
export const createNotificationConfig = async (config: NotificationConfigCreate): Promise<NotificationConfig> => {
  return api.post<NotificationConfig>('/notification-configs', config)
}

/**
 * Update notification config
 */
export const updateNotificationConfig = async (
  workshopId: string,
  config: NotificationConfigUpdate
): Promise<NotificationConfig> => {
  return api.put<NotificationConfig>(`/notification-configs/${workshopId}`, config)
}

/**
 * Create or update notification config (upsert)
 */
export const upsertNotificationConfig = async (config: NotificationConfigCreate): Promise<NotificationConfig> => {
  return api.put<NotificationConfig>(`/notification-configs/${config.workshop_id}/upsert`, config)
}

/**
 * Delete notification config
 */
export const deleteNotificationConfig = async (workshopId: string): Promise<{ ok: boolean; message: string }> => {
  return api.delete<{ ok: boolean; message: string }>(`/notification-configs/${workshopId}`)
}

/**
 * Toggle notifications on/off for a workshop
 */
export const toggleNotifications = async (
  workshopId: string,
  enabled: boolean
): Promise<NotificationConfig> => {
  return api.post<NotificationConfig>(`/notification-configs/${workshopId}/toggle`, null, { enabled })
}
