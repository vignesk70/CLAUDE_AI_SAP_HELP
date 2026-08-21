export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  modules: ['@nuxt/ui'],

  css: ['~/assets/css/main.css'],

  app: {
    head: {
      title: 'Claude Support SAP AI',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content: 'AI-powered SAP support assistant powered by Claude'
        }
      ]
    }
  },

  runtimeConfig: {
    public: {
      // Base URL of the FastAPI backend
      apiBase: 'http://localhost:8000'
    }
  },

  colorMode: {
    preference: 'dark',
    fallback: 'dark'
  }
})
