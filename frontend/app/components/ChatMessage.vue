<script setup lang="ts">
import type { ChatMessage } from '~/composables/useChat'
import { renderMarkdown } from '~/utils/markdown'

const props = defineProps<{ message: ChatMessage }>()
defineEmits<{ followup: [content: string] }>()

const isUser = computed(() => props.message.role === 'user')

const html = computed(() => renderMarkdown(props.message.content))

const confidence = computed(() => {
  switch (props.message.confidence) {
    case 'high':
      return { label: 'High confidence', color: 'success' as const }
    case 'low':
      return { label: 'Low confidence', color: 'warning' as const }
    default:
      return { label: 'Medium confidence', color: 'neutral' as const }
  }
})
</script>

<template>
  <div :class="['flex items-start gap-3', isUser ? 'flex-row-reverse' : 'flex-row']">
    <div
      v-if="!isUser"
      class="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary-600/15 text-primary-500"
    >
      <UIcon name="i-lucide-bot" class="size-4" />
    </div>

    <!-- User message -->
    <div
      v-if="isUser"
      class="bubble-user max-w-[80%] px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap md:max-w-[70%]"
    >
      {{ message.content }}
    </div>

    <!-- Assistant message -->
    <div v-else class="min-w-0 flex-1 space-y-3">
      <div class="bubble-assistant px-4 py-3">
        <div class="md-content" v-html="html" />
      </div>

      <div v-if="message.confidence" class="pl-1">
        <UBadge :color="confidence.color" variant="subtle" size="xs">
          {{ confidence.label }}
        </UBadge>
      </div>

      <div v-if="message.citations?.length" class="pl-1">
        <p class="mb-1.5 text-xs font-medium text-(--ui-text-muted)">Sources</p>
        <ul class="space-y-1.5">
          <li v-for="c in message.citations" :key="c.loio">
            <a :href="c.url" target="_blank" rel="noopener noreferrer" class="citation-link">
              <UIcon name="i-lucide-book-open" class="size-3.5 shrink-0 text-primary-500" />
              <span class="truncate">{{ c.title }}</span>
              <UIcon name="i-lucide-arrow-up-right" class="size-3 shrink-0 opacity-60" />
            </a>
          </li>
        </ul>
      </div>

      <div v-if="message.followupQuestions?.length" class="flex flex-wrap gap-2 pl-1">
        <button
          v-for="q in message.followupQuestions"
          :key="q"
          type="button"
          class="suggestion-chip"
          @click="$emit('followup', q)"
        >
          <UIcon name="i-lucide-corner-down-right" class="size-3.5 shrink-0 text-primary-500" />
          <span>{{ q }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
