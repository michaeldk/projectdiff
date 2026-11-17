<script setup lang="ts">
const model = defineModel<string>({ default: '' })

withDefaults(
  defineProps<{
    rows?: number
    placeholder?: string
    disabled?: boolean
  }>(),
  {
    rows: 6,
    placeholder: '',
    disabled: false,
  },
)
</script>

<template>
  <textarea
    v-model="model"
    class="w-full resize-y rounded border border-border bg-surface px-3 py-2 font-mono text-sm text-fg placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/40"
    :rows="rows"
    :placeholder="placeholder"
    :disabled="disabled"
  />
</template>
