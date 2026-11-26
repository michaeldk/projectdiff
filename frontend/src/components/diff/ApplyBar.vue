<script setup lang="ts">
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'

defineProps<{
  selectedCount: number
  applying?: boolean
  canApply?: boolean
  targetDirty?: boolean
  message?: string | null
  messageTone?: 'success' | 'danger' | 'info' | 'warning'
}>()

const emit = defineEmits<{
  apply: []
  selectAll: []
  clear: []
}>()
</script>

<template>
  <div class="flex flex-col gap-2 px-4 py-3">
    <div class="flex flex-wrap items-center gap-2">
      <span class="text-sm text-fg-muted">
        {{ selectedCount }} line{{ selectedCount === 1 ? '' : 's' }} selected
      </span>
      <div class="ml-auto flex items-center gap-2">
        <UiButton size="sm" variant="ghost" @click="emit('selectAll')">Select all</UiButton>
        <UiButton size="sm" variant="ghost" :disabled="selectedCount === 0" @click="emit('clear')">
          Clear
        </UiButton>
        <UiButton
          variant="primary"
          :disabled="!canApply || selectedCount === 0"
          :loading="applying"
          @click="emit('apply')"
        >
          Apply to B
        </UiButton>
      </div>
    </div>
    <UiAlert v-if="targetDirty" tone="warning">
      Target has uncommitted changes. Apply still works; commit or stash when you are done.
    </UiAlert>
    <UiAlert v-if="message" :tone="messageTone ?? 'info'">{{ message }}</UiAlert>
  </div>
</template>
