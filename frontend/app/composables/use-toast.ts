import { ref, watch } from 'vue'
import type { Component, VNode } from 'vue'

type ToastTitle = string | VNode
type ToastDescription = string | VNode
type ToastAction = {
  label: string
  altText: string
  onClick: (event: MouseEvent) => void
}

interface ToastProps {
  id: string
  title?: ToastTitle
  description?: ToastDescription
  action?: ToastAction
  component?: Component
  props?: Record<string, any>
  duration?: number
  onDismiss?: (toast: ToastProps) => void
  onAutoClose?: (toast: ToastProps) => void
}

interface ToastContext {
  toasts: ToastProps[]
  toast: (toast: Omit<ToastProps, 'id'>) => {
    id: string
    dismiss: () => void
  }
  dismiss: (id: string) => void
}

const toasts = ref<ToastProps[]>([])

function toast(toast: Omit<ToastProps, 'id'>) {
  const id = Math.random().toString(36).substring(2, 9)

  const dismiss = () => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  toasts.value.push({
    id,
    ...toast,
  })

  return {
    id,
    dismiss,
  }
}

function dismiss(id: string) {
  toasts.value = toasts.value.filter(t => t.id !== id)
}

export function useToast(): ToastContext {
  return {
    toasts: toasts.value,
    toast,
    dismiss,
  }
}
