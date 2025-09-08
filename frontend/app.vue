<script setup lang="ts">
// Enable dark mode by default
onMounted(() => {
  // Check if user has a preference stored
  const theme = localStorage.getItem('theme') || 'dark'
  if (theme === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
})

// Set up head tags
useHead({
  htmlAttrs: {
    class: 'dark',
  },
  bodyAttrs: {
    class: 'min-h-screen antialiased',
  },
})
</script>

<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <Toaster />
  </div>
</template>