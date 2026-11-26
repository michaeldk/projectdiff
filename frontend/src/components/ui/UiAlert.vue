<script setup lang="ts">
import { computed } from 'vue'

type Tone = 'info' | 'success' | 'warning' | 'danger'

const props = withDefaults(
  defineProps<{
    tone?: Tone
  }>(),
  { tone: 'info' },
)

const toneClass: Record<Tone, string> = {
  info: 'border-border bg-surface-muted text-fg',
  success: 'border-diff-add-fg/30 bg-diff-add-bg text-diff-add-fg',
  warning: 'border-danger/40 bg-diff-del-bg font-medium text-danger',
  danger: 'border-danger/50 bg-diff-del-bg text-danger',
}

const classes = computed(() => [
  'rounded border px-3 py-2 text-sm',
  toneClass[props.tone],
])
</script>

<template>
  <div role="alert" :class="classes">
    <slot />
  </div>
</template>
