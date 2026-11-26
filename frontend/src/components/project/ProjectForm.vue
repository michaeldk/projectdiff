<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import RepoPicker from '@/components/repo/RepoPicker.vue'
import UiButton from '@/components/ui/UiButton.vue'

const props = withDefaults(
  defineProps<{
    title?: string
    initialName?: string
    pathA: string | null
    pathB: string | null
    picking?: boolean
    saving?: boolean
    submitLabel?: string
  }>(),
  {
    title: 'New project',
    initialName: '',
    picking: false,
    saving: false,
    submitLabel: 'Create project',
  },
)

const emit = defineEmits<{
  pick: [side: 'a' | 'b']
  cancel: []
  submit: [payload: { name: string; pathA: string; pathB: string }]
}>()

const name = ref(props.initialName)

watch(
  () => props.initialName,
  (value) => {
    name.value = value
  },
)

const canSubmit = computed(
  () =>
    Boolean(name.value.trim() && props.pathA && props.pathB) &&
    !props.saving &&
    !props.picking,
)

function onSubmit(): void {
  if (!props.pathA || !props.pathB || !name.value.trim()) return
  emit('submit', {
    name: name.value.trim(),
    pathA: props.pathA,
    pathB: props.pathB,
  })
}
</script>

<template>
  <div class="mx-auto flex h-full w-full max-w-xl flex-col gap-6 p-8">
    <div>
      <h2 class="text-xl font-semibold">{{ title }}</h2>
      <p class="mt-1 text-sm text-fg-muted">
        Choose a name and pick source (A) and destination (B) git repositories.
      </p>
    </div>

    <label class="flex flex-col gap-1">
      <span class="text-xs font-medium uppercase tracking-wide text-fg-muted">Name</span>
      <input
        v-model="name"
        type="text"
        class="rounded border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
        placeholder="My project"
        :disabled="saving"
        @keydown.enter.prevent="onSubmit"
      />
    </label>

    <div class="rounded border border-border">
      <RepoPicker
        :path-a="pathA"
        :path-b="pathB"
        :loading="picking || saving"
        @pick="emit('pick', $event)"
      />
    </div>

    <div class="flex items-center justify-end gap-2">
      <UiButton variant="ghost" size="sm" :disabled="saving" @click="emit('cancel')">
        Cancel
      </UiButton>
      <UiButton
        variant="primary"
        size="sm"
        :disabled="!canSubmit"
        :loading="saving"
        @click="onSubmit"
      >
        {{ submitLabel }}
      </UiButton>
    </div>
  </div>
</template>
