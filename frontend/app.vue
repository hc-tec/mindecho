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
  meta: [
    {
      name: 'referrer',
      content: 'no-referrer',
    },
  ],
})
</script>

<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <ClientOnly>
      <Toaster />
    </ClientOnly>
  </div>
</template>