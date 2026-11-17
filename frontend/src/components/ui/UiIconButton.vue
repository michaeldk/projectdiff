<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    disabled?: boolean
  }>(),
  { disabled: false },
)
</script>

<template>
  <button
    type="button"
    class="inline-flex size-8 items-center justify-center rounded text-fg-muted hover:bg-surface-muted hover:text-fg disabled:opacity-50"
    :aria-label="label"
    :title="label"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>
