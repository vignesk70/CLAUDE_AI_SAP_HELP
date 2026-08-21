<script setup lang="ts">
const emit = defineEmits<{ select: [content: string] }>()

const suggestions = [
  { icon: 'i-lucide-list-checks', label: 'How do I check the status of a background job in SAP?' },
  { icon: 'i-lucide-code', label: 'What is the difference between SE38 and SE80?' },
  { icon: 'i-lucide-database', label: 'Which table stores user master records?' },
  { icon: 'i-lucide-wrench', label: 'How do I troubleshoot a short dump with ST22?' }
]
</script>

<template>
  <div class="flex flex-col items-center justify-center py-12 text-center md:py-20">
    <div class="mb-6 flex size-16 items-center justify-center rounded-2xl bg-primary-600/15">
      <UIcon name="i-lucide-bot" class="size-8 text-primary-500" />
    </div>

    <h2 class="text-2xl font-semibold text-(--ui-text-highlighted)">
      How can I help with SAP today?
    </h2>
    <p class="mt-2 max-w-md text-sm text-(--ui-text-muted)">
      Ask about transactions, ABAP development, database tables, configuration, or error
      troubleshooting.
    </p>

    <div class="mt-8 grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
      <button
        v-for="s in suggestions"
        :key="s.label"
        type="button"
        class="suggestion-chip"
        @click="emit('select', s.label)"
      >
        <UIcon :name="s.icon" class="size-4 shrink-0 text-primary-500" />
        <span>{{ s.label }}</span>
      </button>
    </div>
  </div>
</template>
