<script setup lang="ts">
import type { ChatMessage } from '~/composables/useChat'

const props = defineProps<{ message: ChatMessage }>()

const isUser = computed(() => props.message.role === 'user')
</script>

<template>
  <div :class="['flex items-start gap-3', isUser ? 'flex-row-reverse' : 'flex-row']">
    <div
      v-if="!isUser"
      class="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary-600/15 text-primary-500"
    >
      <UIcon name="i-lucide-bot" class="size-4" />
    </div>

    <div
      :class="[
        'max-w-[80%] px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap md:max-w-[70%]',
        isUser ? 'bubble-user' : 'bubble-assistant'
      ]"
    >
      {{ message.content }}
    </div>
  </div>
</template>
