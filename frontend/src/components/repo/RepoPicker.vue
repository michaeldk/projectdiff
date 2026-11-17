<script setup lang="ts">
import UiButton from '@/components/ui/UiButton.vue'

defineProps<{
  pathA: string | null
  pathB: string | null
  loading?: boolean
}>()

const emit = defineEmits<{
  pick: [side: 'a' | 'b']
}>()

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
    <div class="flex flex-col gap-1">
      <span class="text-xs font-medium uppercase tracking-wide text-fg-muted">Target (B)</span>
      <div class="flex items-center gap-2">
        <UiButton size="sm" :disabled="loading" @click="emit('pick', 'b')">Browse…</UiButton>
        <span class="truncate font-mono text-sm" :title="pathB ?? undefined">
          {{ shortPath(pathB) }}
        </span>
      </div>
    </div>
  </div>
</template>
