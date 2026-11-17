<script setup lang="ts">
import { computed } from 'vue'

import UiButton from '@/components/ui/UiButton.vue'
import UiTextarea from '@/components/ui/UiTextarea.vue'

const props = defineProps<{
  excludes: string[]
  saving?: boolean
}>()

const emit = defineEmits<{
  save: [excludes: string[]]
}>()

const text = defineModel<string>('text', { default: '' })

const dirty = computed(() => {
  const current = text.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  if (current.length !== props.excludes.length) return true
  return current.some((line, i) => line !== props.excludes[i])
})

function onSave(): void {
  const next = text.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  emit('save', next)
}
</script>

<template>
  <div class="flex flex-col gap-2 p-4">
    <div class="flex items-center justify-between gap-2">
      <span class="text-xs font-medium uppercase tracking-wide text-fg-muted">
        Exclude patterns
      </span>
      <UiButton size="sm" :disabled="!dirty || saving" :loading="saving" @click="onSave">
        Save
      </UiButton>
    </div>
    <UiTextarea
      v-model="text"
      :rows="5"
      placeholder="One pattern per line, e.g. node_modules/"
      :disabled="saving"
    />
  </div>
</template>
