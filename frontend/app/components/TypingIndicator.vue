<template>
  <div class="flex items-start gap-3">
    <div
      class="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary-600/15 text-primary-500"
    >
      <UIcon name="i-lucide-bot" class="size-4" />
    </div>
    <div class="bubble-assistant flex items-center gap-1.5 px-4 py-3.5">
      <span class="typing-dot" style="--dot-delay: 0s" />
      <span class="typing-dot" style="--dot-delay: 0.15s" />
      <span class="typing-dot" style="--dot-delay: 0.3s" />
    </div>
  </div>
</template>

<style scoped>
.typing-dot {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 9999px;
  background-color: var(--ui-text-muted);
  animation: typing-bounce 1s infinite ease-in-out;
  animation-delay: var(--dot-delay, 0s);
}

@keyframes typing-bounce {
  0%,
  80%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  40% {
    transform: translateY(-0.25rem);
    opacity: 1;
  }
}
</style>
