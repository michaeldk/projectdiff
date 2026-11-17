<script setup lang="ts">
import { computed } from 'vue'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'
type Size = 'sm' | 'md'

const props = withDefaults(
  defineProps<{
    variant?: Variant
    size?: Size
    loading?: boolean
    disabled?: boolean
    type?: 'button' | 'submit' | 'reset'
  }>(),
  {
    variant: 'secondary',
    size: 'md',
    loading: false,
    disabled: false,
    type: 'button',
  },
)

const variantClass: Record<Variant, string> = {
  primary: 'bg-accent text-white hover:opacity-90',
  secondary: 'border border-border bg-surface text-fg hover:bg-surface-muted',
  danger: 'bg-danger text-white hover:opacity-90',
  ghost: 'text-fg-muted hover:bg-surface-muted hover:text-fg',
}

const sizeClass: Record<Size, string> = {
  sm: 'px-2 py-1 text-xs',
  md: 'px-3 py-1.5 text-sm',
}

const classes = computed(() => [
  'inline-flex items-center justify-center gap-1.5 rounded font-medium transition-opacity',
  'disabled:cursor-not-allowed disabled:opacity-50',
  variantClass[props.variant],
  sizeClass[props.size],
])
</script>

<template>
  <button
    :type="type"
    class="ui-button"
    :class="classes"
    :disabled="disabled || loading"
  >
    <span v-if="loading" class="opacity-70">…</span>
    <slot />
  </button>
</template>
