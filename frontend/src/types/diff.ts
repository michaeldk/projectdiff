/** Mirrors backend `project_diff.diff` dataclasses. */

export type LineKind = 'add' | 'del' | 'ctx'

export type FileSide = 'both' | 'only_a' | 'only_b'

export interface Line {
  id: string
  kind: LineKind
  old_no: number | null
  new_no: number | null
  text: string
}

export interface Hunk {
  old_start: number
  old_count: number
  new_start: number
  new_count: number
  section: string
  lines: Line[]
}

export interface FileDiff {
  path: string
  side: FileSide
  binary: boolean
  hunks: Hunk[]
}

export interface DiffResult {
  diff_id: string
  files: FileDiff[]
}

/** True when the line can be selected for apply. */
export function isSelectableKind(kind: LineKind): boolean {
  return kind === 'add' || kind === 'del'
}

/** Collect selectable line IDs from a hunk. */
export function selectableLineIds(hunk: Hunk): string[] {
  return hunk.lines.filter((l) => isSelectableKind(l.kind)).map((l) => l.id)
}

/** Collect selectable line IDs from a file. */
export function selectableFileLineIds(file: FileDiff): string[] {
  return file.hunks.flatMap(selectableLineIds)
}
