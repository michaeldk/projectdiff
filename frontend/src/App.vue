<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  apply as applyPatch,
  computeDiff,
  createProject,
  deleteProject,
  getSettings,
  listProjects,
  pickFolder,
  saveSettings,
  updateProject,
  waitForBridge,
  type FileEntry,
  type Project,
  type ThemeMode,
} from '@/api'
import ApplyBar from '@/components/diff/ApplyBar.vue'
import FileDiffView from '@/components/diff/FileDiff.vue'
import FileList from '@/components/diff/FileList.vue'
import AppShell from '@/components/layout/AppShell.vue'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'
import ProjectForm from '@/components/project/ProjectForm.vue'
import ProjectList from '@/components/project/ProjectList.vue'
import ExcludeEditor from '@/components/repo/ExcludeEditor.vue'
import RepoPicker from '@/components/repo/RepoPicker.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import { useSelection } from '@/composables/useSelection'
import { useTheme } from '@/composables/useTheme'
import type { DiffResult, FileDiff, Hunk, Line } from '@/types/diff'

type View = 'list' | 'create' | 'workspace'

const { mode, setMode } = useTheme()

const view = ref<View>('list')
const projects = ref<Project[]>([])
const activeProject = ref<Project | null>(null)

const pathA = ref<string | null>(null)
const pathB = ref<string | null>(null)
const projectName = ref('')

const excludes = ref<string[]>([])
const excludeText = ref('')

const fileList = ref<FileEntry[]>([])
const diff = ref<DiffResult | null>(null)
const activePath = ref<string | null>(null)

const picking = ref(false)
const savingSettings = ref(false)
const savingProject = ref(false)
const loadingProjects = ref(false)
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

const shellTitle = computed(() => {
  if (view.value === 'workspace' && activeProject.value) {
    return activeProject.value.name
  }
  return 'Project Diff'
})

function setStatus(
  message: string | null,
  tone: 'success' | 'danger' | 'info' | 'warning' = 'info',
): void {
  statusMessage.value = message
  statusTone.value = tone
}

function clearWorkspaceState(): void {
  activeProject.value = null
  pathA.value = null
  pathB.value = null
  projectName.value = ''
  fileList.value = []
  diff.value = null
  activePath.value = null
}

async function loadSettings(): Promise<void> {
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

async function loadProjects(): Promise<void> {
  if (!window.pywebview?.api) return
  loadingProjects.value = true
  try {
    const result = await listProjects()
    if (!result.ok) {
      setStatus(result.error.message, 'danger')
      return
    }
    projects.value = result.data
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  } finally {
    loadingProjects.value = false
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

    if (view.value === 'workspace' && activeProject.value) {
      await persistActiveProjectPaths()
    }
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  } finally {
    picking.value = false
  }
}

async function persistActiveProjectPaths(): Promise<void> {
  if (!activeProject.value || !pathA.value || !pathB.value) return
  savingProject.value = true
  try {
    const result = await updateProject({
      id: activeProject.value.id,
      path_a: pathA.value,
      path_b: pathB.value,
    })
    if (!result.ok) {
      setStatus(result.error.message, 'danger')
      return
    }
    activeProject.value = result.data
    await refreshProjectsQuietly()
    await onCompute()
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  } finally {
    savingProject.value = false
  }
}

async function persistActiveProjectName(): Promise<void> {
  if (!activeProject.value) return
  const next = projectName.value.trim()
  if (!next || next === activeProject.value.name) return
  savingProject.value = true
  try {
    const result = await updateProject({
      id: activeProject.value.id,
      name: next,
    })
    if (!result.ok) {
      setStatus(result.error.message, 'danger')
      projectName.value = activeProject.value.name
      return
    }
    activeProject.value = result.data
    projectName.value = result.data.name
    await refreshProjectsQuietly()
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  } finally {
    savingProject.value = false
  }
}

async function refreshProjectsQuietly(): Promise<void> {
  try {
    const result = await listProjects()
    if (result.ok) projects.value = result.data
  } catch {
    // Ignore refresh failures; primary action already succeeded.
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

function showList(): void {
  clearWorkspaceState()
  view.value = 'list'
  setStatus(null)
  void loadProjects()
}

function showCreate(): void {
  pathA.value = null
  pathB.value = null
  projectName.value = ''
  view.value = 'create'
  setStatus(null)
}

async function openProject(project: Project): Promise<void> {
  activeProject.value = project
  pathA.value = project.path_a
  pathB.value = project.path_b
  projectName.value = project.name
  fileList.value = []
  diff.value = null
  activePath.value = null
  view.value = 'workspace'
  setStatus(null)
  await onCompute()
}

async function onCreateProject(payload: {
  name: string
  pathA: string
  pathB: string
}): Promise<void> {
  if (!window.pywebview?.api) {
    setStatus('Creating a project requires the pywebview bridge.', 'warning')
    return
  }
  savingProject.value = true
  setStatus(null)
  try {
    const result = await createProject({
      name: payload.name,
      path_a: payload.pathA,
      path_b: payload.pathB,
    })
    if (!result.ok) {
      setStatus(result.error.message, 'danger')
      return
    }
    await refreshProjectsQuietly()
    await openProject(result.data)
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  } finally {
    savingProject.value = false
  }
}

async function onDeleteProject(project: Project): Promise<void> {
  if (!window.pywebview?.api) {
    setStatus('Deleting a project requires the pywebview bridge.', 'warning')
    return
  }
  loadingProjects.value = true
  setStatus(null)
  try {
    const result = await deleteProject(project.id)
    if (!result.ok) {
      setStatus(result.error.message, 'danger')
      return
    }
    projects.value = projects.value.filter((p) => p.id !== project.id)
    setStatus(`Deleted “${project.name}”.`, 'info')
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err), 'danger')
  } finally {
    loadingProjects.value = false
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
  void (async () => {
    const ready = await waitForBridge()
    if (!ready) {
      setStatus(
        'Bridge unavailable — open via pywebview. Dev UI still loads.',
        'warning',
      )
      return
    }
    await loadSettings()
    await loadProjects()
  })()
})
</script>

<template>
  <AppShell :title="shellTitle">
    <template #header-actions>
      <template v-if="view === 'workspace'">
        <UiButton variant="ghost" size="sm" @click="showList">Projects</UiButton>
        <UiButton
          variant="primary"
          size="sm"
          :disabled="!canCompute"
          :loading="computing"
          @click="onCompute"
        >
          Compare
        </UiButton>
      </template>
      <ThemeToggle @change="persistTheme" />
    </template>

    <template v-if="view === 'workspace'" #sidebar>
      <div class="border-b border-border p-4">
        <label class="flex flex-col gap-1">
          <span class="text-xs font-medium uppercase tracking-wide text-fg-muted">
            Project name
          </span>
          <input
            v-model="projectName"
            type="text"
            class="rounded border border-border bg-surface px-2 py-1.5 text-sm outline-none focus:border-accent"
            :disabled="savingProject"
            @blur="persistActiveProjectName"
            @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
          />
        </label>
      </div>
      <RepoPicker
        :path-a="pathA"
        :path-b="pathB"
        :loading="picking || savingProject"
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

    <template v-if="view === 'list'">
      <ProjectList
        :projects="projects"
        :loading="loadingProjects"
        @create="showCreate"
        @open="openProject"
        @delete="onDeleteProject"
      />
      <div v-if="statusMessage" class="px-8 pb-8">
        <UiAlert :tone="statusTone" class="mx-auto max-w-2xl">
          {{ statusMessage }}
        </UiAlert>
      </div>
    </template>

    <template v-else-if="view === 'create'">
      <ProjectForm
        :path-a="pathA"
        :path-b="pathB"
        :picking="picking"
        :saving="savingProject"
        @pick="onPick"
        @cancel="showList"
        @submit="onCreateProject"
      />
      <div v-if="statusMessage" class="px-8 pb-8">
        <UiAlert :tone="statusTone" class="mx-auto max-w-xl">
          {{ statusMessage }}
        </UiAlert>
      </div>
    </template>

    <template v-else>
      <div
        v-if="!diff && computing"
        class="flex h-full flex-col items-center justify-center gap-2 p-8"
      >
        <p class="text-sm text-fg-muted">Comparing…</p>
      </div>

      <div
        v-else-if="!diff"
        class="flex h-full flex-col items-center justify-center gap-2 p-8"
      >
        <p class="text-lg font-medium">No diff yet</p>
        <p class="max-w-md text-center text-sm text-fg-muted">
          Click Compare after choosing source and target folders.
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
    </template>

    <template v-if="view === 'workspace'" #footer>
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
