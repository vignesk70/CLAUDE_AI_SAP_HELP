<script setup lang="ts">
const props = defineProps<{ loading: boolean }>()
const emit = defineEmits<{ send: [content: string] }>()

const input = ref('')

function submit() {
  const content = input.value.trim()
  if (!content || props.loading) return
  emit('send', content)
  input.value = ''
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <div class="shrink-0 border-t border-(--ui-border-muted) px-4 py-4 md:px-6">
    <div class="mx-auto flex max-w-3xl items-end gap-2">
      <UTextarea
        v-model="input"
        :rows="1"
        autoresize
        :maxrows="6"
        placeholder="Ask about SAP errors, ABAP, transactions, or configuration…"
        class="flex-1"
        :disabled="loading"
        @keydown="onKeydown"
      />
      <UButton
        icon="i-lucide-send"
        color="primary"
        size="md"
        :loading="loading"
        :disabled="!input.trim() || loading"
        aria-label="Send message"
        class="mb-0.5"
        @click="submit"
      />
    </div>
    <p class="mx-auto mt-2 max-w-3xl text-center text-xs text-(--ui-text-dimmed)">
      Claude can make mistakes. Verify critical SAP changes in a non-production system first.
    </p>
  </div>
</template>
