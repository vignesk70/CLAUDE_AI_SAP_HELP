<script setup lang="ts">
const { messages, isLoading, error, send, reset } = useChat()

const scrollContainer = useTemplateRef<HTMLDivElement>('scroll')

// Keep the conversation pinned to the latest message
watch(
  [messages, isLoading],
  () => {
    nextTick(() => {
      const el = scrollContainer.value
      if (el) el.scrollTop = el.scrollHeight
    })
  },
  { deep: true }
)

useHead({ title: 'Claude Support SAP AI' })
</script>

<template>
  <div class="flex h-dvh flex-col bg-(--ui-bg)">
    <AppHeader @reset="reset" />

    <main ref="scroll" class="flex-1 overflow-y-auto">
      <div class="mx-auto w-full max-w-3xl px-4 py-6">
        <EmptyState v-if="messages.length === 0" @select="send" />

        <div v-else class="space-y-5">
          <ChatMessage v-for="m in messages" :key="m.id" :message="m" />
          <TypingIndicator v-if="isLoading" />
        </div>

        <UAlert
          v-if="error"
          color="error"
          icon="i-lucide-triangle-alert"
          title="Request failed"
          :description="error"
          class="mt-4"
        />
      </div>
    </main>

    <ChatInput :loading="isLoading" @send="send" />
  </div>
</template>
