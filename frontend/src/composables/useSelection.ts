import { computed, ref, watch, type Ref } from 'vue'

import type { DiffResult, FileDiff, Hunk, LineKind } from '@/types/diff'
import {
  isSelectableKind,
  selectableFileLineIds,
  selectableLineIds,
} from '@/types/diff'

export type CheckState = 'checked' | 'unchecked' | 'indeterminate'

function checkStateForIds(ids: string[], selected: Set<string>): CheckState {
  if (ids.length === 0) return 'unchecked'
  let n = 0
  for (const id of ids) {
    if (selected.has(id)) n += 1
  }
  if (n === 0) return 'unchecked'
  if (n === ids.length) return 'checked'
  return 'indeterminate'
}

function toggleIds(selected: Set<string>, ids: string[]): void {
  if (ids.length === 0) return
  const allOn = ids.every((id) => selected.has(id))
  if (allOn) {
    for (const id of ids) selected.delete(id)
  } else {
    for (const id of ids) selected.add(id)
  }
}

/**
 * Selection state for a DiffResult: a Set of selectable line IDs.
 * Cleared whenever the underlying diff identity changes.
 */
export function useSelection(diff: Ref<DiffResult | null>) {
  const selected = ref<Set<string>>(new Set())

  watch(
    () => diff.value?.diff_id,
    () => {
      selected.value = new Set()
    },
    { flush: 'sync' },
  )

  const selectedCount = computed(() => selected.value.size)

  const allSelectableIds = computed(() => {
    const result = diff.value
    if (!result) return [] as string[]
    return result.files.flatMap(selectableFileLineIds)
  })

  function isSelected(id: string): boolean {
    return selected.value.has(id)
  }

  function toggleLine(id: string, kind: LineKind): void {
    if (!isSelectableKind(kind)) return
    const next = new Set(selected.value)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    selected.value = next
  }

  function toggleHunk(hunk: Hunk): void {
    const ids = selectableLineIds(hunk)
    const next = new Set(selected.value)
    toggleIds(next, ids)
    selected.value = next
  }

  function toggleFile(file: FileDiff): void {
    if (file.binary) return
    const ids = selectableFileLineIds(file)
    const next = new Set(selected.value)
    toggleIds(next, ids)
    selected.value = next
  }

  function selectAll(): void {
    selected.value = new Set(allSelectableIds.value)
  }

  function clear(): void {
    selected.value = new Set()
  }

  function hunkCheckState(hunk: Hunk): CheckState {
    return checkStateForIds(selectableLineIds(hunk), selected.value)
  }

  function fileCheckState(file: FileDiff): CheckState {
    if (file.binary) return 'unchecked'
    return checkStateForIds(selectableFileLineIds(file), selected.value)
  }

  function selectedIds(): string[] {
    return [...selected.value]
  }

  return {
    selected,
    selectedCount,
    isSelected,
    toggleLine,
    toggleHunk,
    toggleFile,
    selectAll,
    clear,
    hunkCheckState,
    fileCheckState,
    selectedIds,
  }
}

export type UseSelection = ReturnType<typeof useSelection>
