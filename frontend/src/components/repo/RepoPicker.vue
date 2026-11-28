<script setup lang="ts">
import { computed } from 'vue'

import UiButton from '@/components/ui/UiButton.vue'

const props = defineProps<{
  pathA: string | null
  pathB: string | null
  loading?: boolean
  canSwap?: boolean
}>()

const emit = defineEmits<{
  pick: [side: 'a' | 'b']
  swap: []
}>()

const swapEnabled = computed(
  () =>
    Boolean(props.pathA && props.pathB) &&
    !props.loading &&
    props.canSwap !== false,
)

function shortPath(path: string | null): string {
  if (!path) return 'Not selected'
  const parts = path.replace(/\\/g, '/').split('/')
  if (parts.length <= 2) return path
  return `…/${parts.slice(-2).join('/')}`
}
</script>

<template>
  <div class="flex flex-col gap-3 p-4">
    <div class="flex flex-col gap-1">
      <span class="text-xs font-medium uppercase tracking-wide text-fg-muted">Source (A)</span>
      <div class="flex items-center gap-2">
        <UiButton size="sm" :disabled="loading" @click="emit('pick', 'a')">Browse…</UiButton>
        <span class="truncate font-mono text-sm" :title="pathA ?? undefined">
          {{ shortPath(pathA) }}
        </span>
      </div>
    </div>
    <div class="flex justify-center">
      <UiButton size="sm" variant="ghost" :disabled="!swapEnabled" @click="emit('swap')">
        Swap
      </UiButton>
    </div>
    <div class="flex flex-col gap-1">
      <span class="text-xs font-medium uppercase tracking-wide text-fg-muted">Destination (B)</span>
      <div class="flex items-center gap-2">
        <UiButton size="sm" :disabled="loading" @click="emit('pick', 'b')">Browse…</UiButton>
        <span class="truncate font-mono text-sm" :title="pathB ?? undefined">
          {{ shortPath(pathB) }}
        </span>
      </div>
    </div>
  </div>
</template>
