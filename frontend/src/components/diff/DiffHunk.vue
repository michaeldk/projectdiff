<script setup lang="ts">
import { computed } from 'vue'

import UiCheckbox from '@/components/ui/UiCheckbox.vue'
import type { CheckState } from '@/composables/useSelection'
import type { Hunk, Line } from '@/types/diff'
import { selectableLineIds } from '@/types/diff'

import DiffLine from './DiffLine.vue'

const props = defineProps<{
  hunk: Hunk
  checkState: CheckState
  isSelected: (id: string) => boolean
}>()

const emit = defineEmits<{
  toggleHunk: []
  toggleLine: [line: Line]
}>()

const canToggle = computed(() => selectableLineIds(props.hunk).length > 0)
const checked = computed(() => props.checkState === 'checked')
const indeterminate = computed(() => props.checkState === 'indeterminate')

const header = computed(() => {
  const base = `@@ -${props.hunk.old_start},${props.hunk.old_count} +${props.hunk.new_start},${props.hunk.new_count} @@`
  return props.hunk.section ? `${base} ${props.hunk.section}` : base
})

function onHunkCheck(value: boolean): void {
  void value
  emit('toggleHunk')
}
</script>

<template>
  <div class="flex flex-col">
    <div class="diff-hunk-header flex items-center gap-2">
      <UiCheckbox
        v-if="canToggle"
        :model-value="checked"
        :indeterminate="indeterminate"
        @update:model-value="onHunkCheck"
      />
      <span>{{ header }}</span>
    </div>
    <DiffLine
      v-for="line in hunk.lines"
      :key="line.id"
      :line="line"
      :selected="isSelected(line.id)"
      @toggle="emit('toggleLine', line)"
    />
  </div>
</template>
