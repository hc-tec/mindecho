import { ref, onUnmounted } from 'vue'

export interface WebSocketOptions {
  reconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useWebSocket(url: string, options: WebSocketOptions = {}) {
  const {
    reconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options

  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const error = ref<Event | null>(null)
  const reconnectAttempts = ref(0)

  const messageHandlers = new Set<(data: any) => void>()

  const connect = () => {
    if (isConnecting.value || isConnected.value) return

    isConnecting.value = true
    error.value = null

    try {
      ws.value = new WebSocket(url)

      ws.value.onopen = () => {
        isConnected.value = true
        isConnecting.value = false
        reconnectAttempts.value = 0
        console.log(`WebSocket connected to ${url}`)
      }

      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          messageHandlers.forEach(handler => handler(data))
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.value.onerror = (event) => {
        error.value = event
        console.error('WebSocket error:', event)
      }

      ws.value.onclose = () => {
        isConnected.value = false
        isConnecting.value = false
        ws.value = null

        if (reconnect && reconnectAttempts.value < maxReconnectAttempts) {
          reconnectAttempts.value++
          console.log(`Reconnecting in ${reconnectInterval}ms... (attempt ${reconnectAttempts.value})`)
          setTimeout(connect, reconnectInterval)
        }
      }
    } catch (e) {
      isConnecting.value = false
      error.value = new Event('connection-failed')
      console.error('Failed to create WebSocket:', e)
    }
  }

  const disconnect = () => {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    isConnected.value = false
    isConnecting.value = false
  }

  const send = (data: any) => {
    if (!isConnected.value || !ws.value) {
      console.warn('WebSocket is not connected')
      return false
    }

    try {
      ws.value.send(JSON.stringify(data))
      return true
    } catch (e) {
      console.error('Failed to send WebSocket message:', e)
      return false
    }
  }

  const onMessage = (handler: (data: any) => void) => {
    messageHandlers.add(handler)
    
    // Return cleanup function
    return () => {
      messageHandlers.delete(handler)
    }
  }

  // Auto-connect on creation
  connect()

  // Cleanup on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected: readonly(isConnected),
    isConnecting: readonly(isConnecting),
    error: readonly(error),
    connect,
    disconnect,
    send,
    onMessage,
  }
}
