<script setup lang="ts">
const baseClass =
  'inline-flex size-8 items-center justify-center rounded text-fg-muted hover:bg-surface-muted hover:text-fg disabled:opacity-50'

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
    :class="baseClass"
    :aria-label="label"
    :title="label"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>
