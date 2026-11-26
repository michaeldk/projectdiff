<script setup lang="ts">
import type { Project } from '@/api'
import UiButton from '@/components/ui/UiButton.vue'

defineProps<{
  projects: Project[]
  loading?: boolean
}>()

const emit = defineEmits<{
  create: []
  open: [project: Project]
  delete: [project: Project]
}>()

function shortPath(path: string): string {
  const parts = path.replace(/\\/g, '/').split('/')
  if (parts.length <= 2) return path
  return `…/${parts.slice(-2).join('/')}`
}
</script>

<template>
  <div class="mx-auto flex h-full w-full max-w-2xl flex-col gap-6 p-8">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-xl font-semibold">Projects</h2>
        <p class="mt-1 text-sm text-fg-muted">
          Each project is a source and destination folder pair. Open one to compare and apply.
        </p>
      </div>
      <UiButton variant="primary" size="sm" :disabled="loading" @click="emit('create')">
        New project
      </UiButton>
    </div>

    <div
      v-if="projects.length === 0"
      class="rounded border border-dashed border-border px-6 py-12 text-center text-sm text-fg-muted"
    >
      No projects yet. Create one to get started.
    </div>

    <ul v-else class="flex flex-col gap-2">
      <li
        v-for="project in projects"
        :key="project.id"
        class="flex items-center gap-3 rounded border border-border bg-surface px-4 py-3"
      >
        <button
          type="button"
          class="min-w-0 flex-1 text-left hover:opacity-90"
          :disabled="loading"
          @click="emit('open', project)"
        >
          <div class="truncate font-medium">{{ project.name }}</div>
          <div class="mt-1 truncate font-mono text-xs text-fg-muted">
            {{ shortPath(project.path_a) }}
            <span class="mx-1 text-fg-muted/60">→</span>
            {{ shortPath(project.path_b) }}
          </div>
        </button>
        <UiButton
          variant="ghost"
          size="sm"
          :disabled="loading"
          @click="emit('delete', project)"
        >
          Delete
        </UiButton>
      </li>
    </ul>
  </div>
</template>
