export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",
  modules: ['shadcn-nuxt', '@pinia/nuxt', '@nuxtjs/tailwindcss'],
  pages: true,
  shadcn: {
    prefix: '',
    componentDir: './app/components/ui'
  },
  devtools: { enabled: true },
  css: ['~/assets/css/main.css'],
  devServer: {
    port: 3001,
  },
  imports: {
    dirs: [
      'stores',
      'composables',
      'utils',
    ],
  },
  components: {
    dirs: [
      {
        path: '~/app/components',
        pathPrefix: false,
      },
    ],
  },
  typescript: {
    strict: true,
    shim: false,
  },
  pinia: {
    storesDirs: ['./app/stores/**'],
  },
});