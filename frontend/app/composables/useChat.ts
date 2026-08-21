export interface HelpCitation {
  loio: string
  title: string
  url: string
}

export type Confidence = 'high' | 'medium' | 'low'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  /** Assistant-only metadata returned by the grounded ask endpoint. */
  citations?: HelpCitation[]
  confidence?: Confidence
  followupQuestions?: string[]
}

/** Response shape of POST /api/help/ask (mirrors `AskResponse` in the backend). */
interface AskResponse {
  question: string
  needed_for_help_input: boolean
  reasoning: string
  search_queries: string[]
  answer: string
  citations: HelpCitation[]
  confidence: Confidence
  followup_questions: string[]
  retrieved_documents: unknown[]
  model: string
}

/**
 * Manages the chat conversation state and communicates with the FastAPI backend.
 * Uses the grounded `POST /api/help/ask` endpoint so answers can carry citations,
 * a confidence level and suggested follow-up questions.
 */
export function useChat() {
  const config = useRuntimeConfig()

  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  function genId(): string {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
  }

  /** Send a question and append the grounded assistant reply to the conversation. */
  async function send(content: string) {
    const trimmed = content.trim()
    if (!trimmed || isLoading.value) return

    error.value = null
    // Prior turns form the history; the new question is sent separately.
    const history = messages.value.map((m) => ({ role: m.role, content: m.content }))
    messages.value.push({ id: genId(), role: 'user', content: trimmed })
    isLoading.value = true

    try {
      const res = await $fetch<AskResponse>(`${config.public.apiBase}/api/help/ask`, {
        method: 'POST',
        body: { question: trimmed, history, max_documents: 6 }
      })
      messages.value.push({
        id: genId(),
        role: 'assistant',
        content: res.answer,
        citations: res.citations,
        confidence: res.confidence,
        followupQuestions: res.followup_questions
      })
    } catch (e: unknown) {
      const err = e as { data?: { detail?: unknown }; message?: string }
      const detail = err?.data?.detail
      error.value =
        typeof detail === 'string'
          ? detail
          : err?.message ?? 'Unable to reach the assistant. Please try again.'
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
