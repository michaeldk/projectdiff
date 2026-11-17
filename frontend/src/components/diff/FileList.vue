<script setup lang="ts">
import type { FileEntry } from '@/api/types'
import type { CheckState } from '@/composables/useSelection'
import type { FileDiff } from '@/types/diff'
import { selectableFileLineIds } from '@/types/diff'

import FileListItem from './FileListItem.vue'

const props = defineProps<{
  entries: FileEntry[]
  filesByPath: Map<string, FileDiff>
  activePath: string | null
  fileCheckState: (file: FileDiff) => CheckState
}>()

const emit = defineEmits<{
  select: [path: string]
  toggle: [file: FileDiff]
}>()

function isSelectable(entry: FileEntry): boolean {
  if (entry.binary) return false
  const file = props.filesByPath.get(entry.path)
  if (!file) return false
  return selectableFileLineIds(file).length > 0
}

function checkFor(entry: FileEntry): CheckState {
  const file = props.filesByPath.get(entry.path)
  if (!file) return 'unchecked'
  return props.fileCheckState(file)
}

function onToggle(entry: FileEntry): void {
  const file = props.filesByPath.get(entry.path)
  if (file) emit('toggle', file)
}
</script>

<template>
  <div class="flex flex-col gap-0.5 p-2">
    <p v-if="entries.length === 0" class="px-2 py-4 text-sm text-fg-muted">No differing files.</p>
    <FileListItem
      v-for="entry in entries"
      :key="entry.path"
      :entry="entry"
      :active="entry.path === activePath"
      :check-state="checkFor(entry)"
      :selectable="isSelectable(entry)"
      @select="emit('select', entry.path)"
      @toggle="onToggle(entry)"
    />
  </div>
</template>
