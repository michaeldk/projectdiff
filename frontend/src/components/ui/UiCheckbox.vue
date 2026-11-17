<script setup lang="ts">
import { ref, watch } from 'vue'

const inputClass = 'size-3.5 accent-accent'
const labelClass = 'inline-flex items-center gap-2 text-sm text-fg'

const props = withDefaults(
  defineProps<{
    modelValue?: boolean
    indeterminate?: boolean
    disabled?: boolean
    label?: string
  }>(),
  {
    modelValue: false,
    indeterminate: false,
    disabled: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const inputRef = ref<HTMLInputElement | null>(null)

watch(
  () => props.indeterminate,
  (value) => {
    if (inputRef.value) inputRef.value.indeterminate = value
  },
  { immediate: true },
)

watch(inputRef, (el) => {
  if (el) el.indeterminate = props.indeterminate
})

function onChange(event: Event): void {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.checked)
}
</script>

<template>
  <label :class="[labelClass, { 'opacity-50': disabled }]">
    <input
      ref="inputRef"
      type="checkbox"
      :class="inputClass"
      :checked="modelValue"
      :disabled="disabled"
      @change="onChange"
    />
    <span v-if="label || $slots.default"><slot>{{ label }}</slot></span>
  </label>
</template>
