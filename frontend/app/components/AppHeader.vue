<script setup lang="ts">
defineEmits<{ reset: [] }>()

const colorMode = useColorMode()

const isDark = computed({
  get: () => colorMode.value === 'dark',
  set: () => {
    colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
  }
})
</script>

<template>
  <header
    class="flex h-16 shrink-0 items-center justify-between border-b border-(--ui-border-muted) px-4 md:px-6"
  >
    <div class="flex items-center gap-3">
      <div
        class="flex size-9 items-center justify-center rounded-xl bg-primary-600 text-(--ui-text-inverted)"
      >
        <UIcon name="i-lucide-bot" class="size-5" />
      </div>
      <div>
        <h1 class="text-sm font-semibold text-(--ui-text-highlighted)">Claude Support SAP AI</h1>
        <p class="text-xs text-(--ui-text-muted)">Your SAP troubleshooting assistant</p>
      </div>
    </div>

    <div class="flex items-center gap-1">
      <UButton
        icon="i-lucide-plus"
        label="New chat"
        color="neutral"
        variant="ghost"
        size="sm"
        @click="$emit('reset')"
      />
      <ClientOnly>
        <UButton
          :icon="isDark ? 'i-lucide-moon' : 'i-lucide-sun'"
          color="neutral"
          variant="ghost"
          size="sm"
          aria-label="Toggle color theme"
          @click="isDark = !isDark"
        />
        <template #fallback>
          <div class="size-8" />
        </template>
      </ClientOnly>
    </div>
  </header>
</template>
