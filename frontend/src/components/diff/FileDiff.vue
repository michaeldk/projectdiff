<script setup lang="ts">
import { computed } from 'vue'

import UiAlert from '@/components/ui/UiAlert.vue'
import UiBadge from '@/components/ui/UiBadge.vue'
import UiCheckbox from '@/components/ui/UiCheckbox.vue'
import type { CheckState } from '@/composables/useSelection'
import type { FileDiff as FileDiffModel, Line } from '@/types/diff'
import { selectableFileLineIds } from '@/types/diff'

import DiffHunk from './DiffHunk.vue'

const props = defineProps<{
  file: FileDiffModel
  checkState: CheckState
  hunkCheckState: (hunk: FileDiffModel['hunks'][number]) => CheckState
  isSelected: (id: string) => boolean
}>()

const emit = defineEmits<{
  toggleFile: []
  toggleHunk: [hunk: FileDiffModel['hunks'][number]]
  toggleLine: [line: Line]
}>()

const canToggle = computed(
  () => !props.file.binary && selectableFileLineIds(props.file).length > 0,
)
const checked = computed(() => props.checkState === 'checked')
const indeterminate = computed(() => props.checkState === 'indeterminate')

const sideLabel = computed(() => {
  if (props.file.side === 'only_a') return 'only in A'
  if (props.file.side === 'only_b') return 'only in B'
  return 'in both'
})

function onFileCheck(value: boolean): void {
  void value
  emit('toggleFile')
}
</script>

<template>
  <div class="flex flex-col">
    <div class="flex items-center gap-2 border-b border-border bg-surface-muted px-3 py-2">
      <UiCheckbox
        v-if="canToggle"
        :model-value="checked"
        :indeterminate="indeterminate"
        @update:model-value="onFileCheck"
      />
      <span class="font-mono text-sm font-medium">{{ file.path }}</span>
      <UiBadge :tone="file.side === 'only_a' ? 'added' : file.side === 'only_b' ? 'removed' : 'modified'">
        {{ sideLabel }}
      </UiBadge>
    </div>

    <UiAlert v-if="file.binary" tone="warning" class="m-3">
      Binary file — not supported for diff or apply.
    </UiAlert>

    <template v-else>
      <p v-if="file.hunks.length === 0" class="p-4 text-sm text-fg-muted">No changes in this file.</p>
      <DiffHunk
        v-for="(hunk, index) in file.hunks"
        :key="`${file.path}:${index}`"
        :hunk="hunk"
        :check-state="hunkCheckState(hunk)"
        :is-selected="isSelected"
        @toggle-hunk="emit('toggleHunk', hunk)"
        @toggle-line="emit('toggleLine', $event)"
      />
    </template>
  </div>
</template>
