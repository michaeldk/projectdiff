<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  apply as applyPatch,
  computeDiff,
  getSettings,
  pickFolder,
  saveSettings,
  type FileEntry,
  type ThemeMode,
} from '@/api'
import ApplyBar from '@/components/diff/ApplyBar.vue'
import FileDiffView from '@/components/diff/FileDiff.vue'
import FileList from '@/components/diff/FileList.vue'
import AppShell from '@/components/layout/AppShell.vue'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'
import ExcludeEditor from '@/components/repo/ExcludeEditor.vue'
import RepoPicker from '@/components/repo/RepoPicker.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import { useSelection } from '@/composables/useSelection'
import { useTheme } from '@/composables/useTheme'
import type { DiffResult, FileDiff, Hunk, Line } from '@/types/diff'

const { mode, setMode } = useTheme()

const pathA = ref<string | null>(null)
const pathB = ref<string | null>(null)
const excludes = ref<string[]>([])
const excludeText = ref('')

const fileList = ref<FileEntry[]>([])
const diff = ref<DiffResult | null>(null)
const activePath = ref<string | null>(null)

const picking = ref(false)
const savingSettings = ref(false)
const computing = ref(false)
const applying = ref(false)

const statusMessage = ref<string | null>(null)
const statusTone = ref<'success' | 'danger' | 'info' | 'warning'>('info')

const {
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
} = useSelection(diff)

const filesByPath = computed(() => {
  const map = new Map<string, FileDiff>()
  for (const file of diff.value?.files ?? []) {
    map.set(file.path, file)
  }
  return map
})

const activeFile = computed(() => {
  if (!activePath.value) return null
  return filesByPath.value.get(activePath.value) ?? null
})

const canCompute = computed(
  () => Boolean(pathA.value && pathB.value) && !computing.value,
)

const canApply = computed(
  () => Boolean(diff.value) && selectedCount.value > 0 && !applying.value,
)

function setStatus(
  message: string | null,
  tone: 'success' | 'danger' | 'info' | 'warning' = 'info',
): void {
  statusMessage.value = message
  statusTone.value = tone
}

async function loadSettings(): Promise<void> {
  if (!window.pywebview?.api) {
    setStatus(
      'Bridge unavailable — open via pywebview. Dev UI still loads.',
      'warning',
    )
    return
  }
  try {
    const result = await getSettings()
    if (!result.ok) {
      setStatus(result.error.message, 'danger')
      return
    }
    excludes.value = result.data.excludes
    excludeText.value = result.data.excludes.join('\n')
    setMode(result.data.theme)
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  }
}

async function persistTheme(): Promise<void> {
  if (!window.pywebview?.api) return
  try {
    const result = await saveSettings({ theme: mode.value as ThemeMode })
    if (!result.ok) setStatus(result.error.message, 'danger')
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  }
}

async function onPick(side: 'a' | 'b'): Promise<void> {
  if (!window.pywebview?.api) {
    setStatus('Folder picker requires the pywebview bridge.', 'warning')
    return
  }
  picking.value = true
  setStatus(null)
  try {
    const result = await pickFolder(side)
    if (!result.ok) {
      setStatus(result.error.message, 'danger')
      return
    }
    if (result.data === null) return
    if (result.data.side === 'a') pathA.value = result.data.path
    else pathB.value = result.data.path
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  } finally {
    picking.value = false
  }
}

async function onSaveExcludes(next: string[]): Promise<void> {
  if (!window.pywebview?.api) {
    excludes.value = next
    excludeText.value = next.join('\n')
    return
  }
  savingSettings.value = true
  try {
    const result = await saveSettings({ excludes: next })
    if (!result.ok) {
      setStatus(result.error.message, 'danger')
      return
    }
    excludes.value = result.data.excludes
    excludeText.value = result.data.excludes.join('\n')
    setStatus('Exclude list saved.', 'success')
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  } finally {
    savingSettings.value = false
  }
}

async function onCompute(): Promise<void> {
  if (!pathA.value || !pathB.value) return
  if (!window.pywebview?.api) {
    setStatus('Diff requires the pywebview bridge.', 'warning')
    return
  }
  computing.value = true
  setStatus(null)
  try {
    const result = await computeDiff(pathA.value, pathB.value)
    if (!result.ok) {
      setStatus(result.error.message, 'danger')
      return
    }
    fileList.value = result.data.file_list
    diff.value = result.data.diff
    activePath.value = result.data.file_list[0]?.path ?? null
    const n = result.data.diff.files.length
    setStatus(`Compared — ${n} differing file${n === 1 ? '' : 's'}.`, 'info')
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  } finally {
    computing.value = false
  }
}

async function onApply(): Promise<void> {
  if (!diff.value) return
  if (!window.pywebview?.api) {
    setStatus('Apply requires the pywebview bridge.', 'warning')
    return
  }
  applying.value = true
  setStatus(null)
  try {
    const result = await applyPatch(diff.value.diff_id, selectedIds())
    if (!result.ok) {
      const hint =
        result.error.code === 'APPLY_CHECK_FAILED'
          ? ' Re-diff if the target changed.'
          : ''
      setStatus(`${result.error.message}${hint}`, 'danger')
      return
    }
    const names = result.data.files.join(', ') || '(none)'
    setStatus(`Applied to: ${names}`, 'success')
    await onCompute()
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  } finally {
    applying.value = false
  }
}

function onToggleLine(line: Line): void {
  toggleLine(line.id, line.kind)
}

function onToggleActiveFile(): void {
  if (activeFile.value) toggleFile(activeFile.value)
}

function onToggleHunk(hunk: Hunk): void {
  toggleHunk(hunk)
}

onMounted(() => {
  void loadSettings()
})
</script>

<template>
  <AppShell>
    <template #header-actions>
      <UiButton
        variant="primary"
        size="sm"
        :disabled="!canCompute"
        :loading="computing"
        @click="onCompute"
      >
        Compare
      </UiButton>
      <ThemeToggle @change="persistTheme" />
    </template>

    <template #sidebar>
      <RepoPicker
        :path-a="pathA"
        :path-b="pathB"
        :loading="picking"
        @pick="onPick"
      />
      <div class="border-t border-border">
        <ExcludeEditor
          v-model:text="excludeText"
          :excludes="excludes"
          :saving="savingSettings"
          @save="onSaveExcludes"
        />
      </div>
      <div class="border-t border-border">
        <div class="px-4 pt-3 text-xs font-medium uppercase tracking-wide text-fg-muted">
          Files
        </div>
        <FileList
          :entries="fileList"
          :files-by-path="filesByPath"
          :active-path="activePath"
          :file-check-state="fileCheckState"
          @select="activePath = $event"
          @toggle="toggleFile"
        />
      </div>
    </template>

    <div v-if="!diff" class="flex h-full flex-col items-center justify-center gap-2 p-8">
      <p class="text-lg font-medium">Compare two git repositories</p>
      <p class="max-w-md text-center text-sm text-fg-muted">
        Pick source (A) and target (B), optionally edit excludes, then click Compare.
        Select lines and apply them into B's working tree.
      </p>
      <UiAlert v-if="statusMessage" :tone="statusTone" class="mt-4 max-w-lg">
        {{ statusMessage }}
      </UiAlert>
    </div>

    <FileDiffView
      v-else-if="activeFile"
      :file="activeFile"
      :check-state="fileCheckState(activeFile)"
      :hunk-check-state="hunkCheckState"
      :is-selected="isSelected"
      @toggle-file="onToggleActiveFile"
      @toggle-hunk="onToggleHunk"
      @toggle-line="onToggleLine"
    />

    <div v-else class="p-8 text-sm text-fg-muted">Select a file from the list.</div>

    <template #footer>
      <ApplyBar
        :selected-count="selectedCount"
        :applying="applying"
        :can-apply="canApply"
        :message="diff ? statusMessage : null"
        :message-tone="statusTone"
        @apply="onApply"
        @select-all="selectAll"
        @clear="clear"
      />
    </template>
  </AppShell>
</template>
