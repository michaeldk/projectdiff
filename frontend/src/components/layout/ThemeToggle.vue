<script setup lang="ts">
import { computed } from 'vue'

import UiIconButton from '@/components/ui/UiIconButton.vue'
import { useTheme } from '@/composables/useTheme'

const emit = defineEmits<{
  change: []
}>()

const { mode, cycle } = useTheme()

const label = computed(() => {
  if (mode.value === 'system') return 'Theme: system'
  if (mode.value === 'light') return 'Theme: light'
  return 'Theme: dark'
})

const glyph = computed(() => {
  if (mode.value === 'system') return '◐'
  if (mode.value === 'light') return '☀'
  return '☾'
})

function onClick(): void {
  cycle()
  emit('change')
}
</script>

<template>
  <UiIconButton :label="label" @click="onClick">
    <span class="text-base leading-none" aria-hidden="true">{{ glyph }}</span>
  </UiIconButton>
</template>
