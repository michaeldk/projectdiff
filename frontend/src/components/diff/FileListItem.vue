<script setup lang="ts">
import { computed } from 'vue'

import UiBadge from '@/components/ui/UiBadge.vue'
import UiCheckbox from '@/components/ui/UiCheckbox.vue'
import type { CheckState } from '@/composables/useSelection'
import type { FileEntry } from '@/api/types'
import type { FileSide } from '@/types/diff'

const props = defineProps<{
  entry: FileEntry
  active: boolean
  checkState: CheckState
  selectable: boolean
}>()

const emit = defineEmits<{
  select: []
  toggle: []
}>()

const badgeTone = computed(() => {
  if (props.entry.binary) return 'warning' as const
  const side = props.entry.side as FileSide
  if (side === 'only_a') return 'added' as const
  if (side === 'only_b') return 'removed' as const
  return 'modified' as const
})

const badgeLabel = computed(() => {
  if (props.entry.binary) return 'binary'
  const side = props.entry.side as FileSide
  if (side === 'only_a') return 'only A'
  if (side === 'only_b') return 'only B'
  return 'both'
})

const checked = computed(() => props.checkState === 'checked')
const indeterminate = computed(() => props.checkState === 'indeterminate')

function onCheck(value: boolean): void {
  void value
  emit('toggle')
}
</script>

<template>
  <div class="sidebar-item" :class="{ 'bg-surface-muted': active }">
    <UiCheckbox
      v-if="selectable"
      :model-value="checked"
      :indeterminate="indeterminate"
      @update:model-value="onCheck"
    />
    <button
      type="button"
      class="min-w-0 flex-1 truncate text-left font-mono text-xs"
      :title="entry.path"
      @click="emit('select')"
    >
      {{ entry.path }}
    </button>
    <UiBadge :tone="badgeTone">{{ badgeLabel }}</UiBadge>
  </div>
</template>
