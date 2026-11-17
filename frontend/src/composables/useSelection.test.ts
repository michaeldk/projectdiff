import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import type { DiffResult, FileDiff, Hunk, Line } from '@/types/diff'

import { useSelection } from './useSelection'

function line(id: string, kind: Line['kind'], text = ''): Line {
  return { id, kind, old_no: null, new_no: null, text }
}

function hunk(lines: Line[]): Hunk {
  return {
    old_start: 1,
    old_count: 1,
    new_start: 1,
    new_count: 1,
    section: '',
    lines,
  }
}

function file(path: string, hunks: Hunk[], side: FileDiff['side'] = 'both'): FileDiff {
  return { path, side, binary: false, hunks }
}

function sampleDiff(): DiffResult {
  return {
    diff_id: 'd1',
    files: [
      file('a.ts', [
        hunk([
          line('0:0:0', 'ctx', 'keep'),
          line('0:0:1', 'del', 'old'),
          line('0:0:2', 'add', 'new'),
          line('0:0:3', 'add', 'also'),
        ]),
        hunk([line('0:1:0', 'del', 'gone'), line('0:1:1', 'ctx', 'stay')]),
      ]),
      file('b.ts', [hunk([line('1:0:0', 'add', 'only')])]),
    ],
  }
}

describe('useSelection', () => {
  it('toggles a selectable line and ignores context', () => {
    const diff = ref<DiffResult | null>(sampleDiff())
    const sel = useSelection(diff)

    sel.toggleLine('0:0:0', 'ctx')
    expect(sel.selectedCount.value).toBe(0)

    sel.toggleLine('0:0:1', 'del')
    expect(sel.isSelected('0:0:1')).toBe(true)
    expect(sel.selectedCount.value).toBe(1)

    sel.toggleLine('0:0:1', 'del')
    expect(sel.isSelected('0:0:1')).toBe(false)
  })

  it('toggles a hunk: all on when partial or empty, all off when full', () => {
    const diff = ref<DiffResult | null>(sampleDiff())
    const sel = useSelection(diff)
    const h0 = diff.value!.files[0]!.hunks[0]!

    expect(sel.hunkCheckState(h0)).toBe('unchecked')

    sel.toggleHunk(h0)
    expect(sel.hunkCheckState(h0)).toBe('checked')
    expect(sel.isSelected('0:0:1')).toBe(true)
    expect(sel.isSelected('0:0:2')).toBe(true)
    expect(sel.isSelected('0:0:3')).toBe(true)
    expect(sel.isSelected('0:0:0')).toBe(false)

    sel.toggleLine('0:0:2', 'add')
    expect(sel.hunkCheckState(h0)).toBe('indeterminate')

    sel.toggleHunk(h0)
    expect(sel.hunkCheckState(h0)).toBe('checked')

    sel.toggleHunk(h0)
    expect(sel.hunkCheckState(h0)).toBe('unchecked')
  })

  it('toggles a file across hunks and reports tri-state', () => {
    const diff = ref<DiffResult | null>(sampleDiff())
    const sel = useSelection(diff)
    const f0 = diff.value!.files[0]!

    sel.toggleFile(f0)
    expect(sel.fileCheckState(f0)).toBe('checked')
    expect(sel.isSelected('0:1:0')).toBe(true)

    sel.toggleLine('0:0:1', 'del')
    expect(sel.fileCheckState(f0)).toBe('indeterminate')

    sel.toggleFile(f0)
    expect(sel.fileCheckState(f0)).toBe('checked')
  })

  it('selectAll selects every add/del line', () => {
    const diff = ref<DiffResult | null>(sampleDiff())
    const sel = useSelection(diff)

    sel.selectAll()
    expect(sel.selectedCount.value).toBe(5)
    expect(sel.selectedIds().sort()).toEqual(
      ['0:0:1', '0:0:2', '0:0:3', '0:1:0', '1:0:0'].sort(),
    )
  })

  it('clears selection when diff_id changes', () => {
    const diff = ref<DiffResult | null>(sampleDiff())
    const sel = useSelection(diff)

    sel.selectAll()
    expect(sel.selectedCount.value).toBe(5)

    diff.value = { ...sampleDiff(), diff_id: 'd2' }
    expect(sel.selectedCount.value).toBe(0)
  })

  it('skips binary files for toggle and check state', () => {
    const binary: FileDiff = {
      path: 'img.bin',
      side: 'both',
      binary: true,
      hunks: [],
    }
    const diff = ref<DiffResult | null>({
      diff_id: 'bin',
      files: [binary],
    })
    const sel = useSelection(diff)

    sel.toggleFile(binary)
    expect(sel.selectedCount.value).toBe(0)
    expect(sel.fileCheckState(binary)).toBe('unchecked')
  })
})
