<script setup lang="ts">
/**
 * BilibiliImage - Universal image component for displaying Bilibili images
 * 
 * Handles Bilibili's anti-hotlinking protection by setting referrerpolicy="no-referrer"
 * 
 * Props:
 *   - src: Image URL
 *   - alt: Alt text for accessibility
 *   - img-class: CSS classes to apply to the image/fallback div
 *   - fallback: Whether to show fallback text on error (default: true)
 * 
 * Usage:
 *   <BilibiliImage :src="item.cover_url" :alt="item.title" img-class="w-24 h-16 rounded" />
 * 
 * Works for any external image source, not just Bilibili.
 */
import { ref } from 'vue'

interface Props {
  src?: string | null
  alt?: string
  imgClass?: string
  fallback?: string
}

const props = withDefaults(defineProps<Props>(), {
  alt: '',
  imgClass: '',
  fallback: 'https://via.placeholder.com/300x200?text=No+Image',
})

const imgError = ref(false)

const handleError = () => {
  imgError.value = true
}
</script>

<template>
  <img 
    v-if="src && !imgError"
    :src="src"
    :alt="alt"
    :class="imgClass"
    referrerpolicy="no-referrer"
    @error="handleError"
  />
  <div 
    v-else-if="fallback"
    :class="[imgClass, 'bg-muted flex items-center justify-center text-muted-foreground text-xs']"
  >
    {{ alt || '暂无封面' }}
  </div>
</template>

