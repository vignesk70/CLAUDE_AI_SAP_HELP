export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

/**
 * Manages the chat conversation state and communicates with the FastAPI backend.
 */
export function useChat() {
  const config = useRuntimeConfig()

  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  function genId(): string {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
  }

  /** Send a user message and stream the assistant reply into the conversation. */
  async function send(content: string) {
    const trimmed = content.trim()
    if (!trimmed || isLoading.value) return

    error.value = null
    messages.value.push({ id: genId(), role: 'user', content: trimmed })
    isLoading.value = true

    try {
      const payload = messages.value.map((m) => ({ role: m.role, content: m.content }))
      const res = await $fetch<{ reply: string }>(`${config.public.apiBase}/api/chat`, {
        method: 'POST',
        body: { messages: payload }
      })
      messages.value.push({ id: genId(), role: 'assistant', content: res.reply })
    } catch (e: unknown) {
      const err = e as { data?: { detail?: string }; message?: string }
      error.value =
        err?.data?.detail ?? err?.message ?? 'Unable to reach the assistant. Please try again.'
    } finally {
      isLoading.value = false
    }
  }

  /** Clear the conversation. */
  function reset() {
    messages.value = []
    error.value = null
  }

  return { messages, isLoading, error, send, reset }
}
