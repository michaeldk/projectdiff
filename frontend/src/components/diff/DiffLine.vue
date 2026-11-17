<script setup lang="ts">
import { computed } from 'vue'

import UiCheckbox from '@/components/ui/UiCheckbox.vue'
import type { Line } from '@/types/diff'
import { isSelectableKind } from '@/types/diff'

const props = defineProps<{
  line: Line
  selected: boolean
}>()

const emit = defineEmits<{
  toggle: []
}>()

const selectable = computed(() => isSelectableKind(props.line.kind))

const lineClass = computed(() => {
  if (props.line.kind === 'add') return 'diff-line diff-line--add'
  if (props.line.kind === 'del') return 'diff-line diff-line--del'
  return 'diff-line'
})

const marker = computed(() => {
  if (props.line.kind === 'add') return '+'
  if (props.line.kind === 'del') return '-'
  return ' '
})

function onCheck(value: boolean): void {
  void value
  emit('toggle')
}
</script>

<template>
  <div class="flex items-stretch" :class="lineClass">
    <div class="flex w-8 shrink-0 items-center justify-center">
      <UiCheckbox
        v-if="selectable"
        :model-value="selected"
        @update:model-value="onCheck"
      />
    </div>
    <span class="diff-gutter w-10 shrink-0">{{ line.old_no ?? '' }}</span>
    <span class="diff-gutter w-10 shrink-0">{{ line.new_no ?? '' }}</span>
    <span class="w-4 shrink-0 select-none text-center opacity-70">{{ marker }}</span>
    <pre class="min-w-0 flex-1 overflow-x-auto whitespace-pre px-1">{{ line.text }}</pre>
  </div>
</template>
