<script setup lang="ts">
import { useToast } from '@/composables/use-toast'
import { Toaster as RadixToaster } from 'radix-vue'

const { toasts } = useToast()
</script>

<template>
  <RadixToaster :toasts="toasts" />
</template>
