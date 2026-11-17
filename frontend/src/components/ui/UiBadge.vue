<script setup lang="ts">
import { computed } from 'vue'

type Tone = 'added' | 'removed' | 'modified' | 'neutral' | 'warning'

const props = withDefaults(
  defineProps<{
    tone?: Tone
  }>(),
  { tone: 'neutral' },
)

const toneClass: Record<Tone, string> = {
  added: 'bg-diff-add-bg text-diff-add-fg',
  removed: 'bg-diff-del-bg text-diff-del-fg',
  modified: 'bg-surface-muted text-accent',
  neutral: 'bg-surface-muted text-fg-muted',
  warning: 'bg-surface-muted text-danger',
}

const classes = computed(() => [
  'inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium',
  toneClass[props.tone],
])
</script>

<template>
  <span :class="classes">
    <slot />
  </span>
</template>
