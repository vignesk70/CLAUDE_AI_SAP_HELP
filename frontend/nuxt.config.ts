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
  },

  // Bundle every icon we use into the client so glyphs render without a
  // network round-trip (Nuxt Icon only auto-bundles its own internal icons).
  icon: {
    serverBundle: 'local',
    clientBundle: {
      icons: [
        'lucide:bot',
        'lucide:plus',
        'lucide:moon',
        'lucide:sun',
        'lucide:send',
        'lucide:book-open',
        'lucide:arrow-up-right',
        'lucide:corner-down-right',
        'lucide:list-checks',
        'lucide:code',
        'lucide:database',
        'lucide:wrench',
        'lucide:triangle-alert'
      ],
      sizeLimitKb: 0
    }
  }
})
