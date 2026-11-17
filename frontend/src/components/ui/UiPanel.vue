<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    padding?: boolean
  }>(),
  { padding: true },
)

const classes = computed(() => [
  'panel',
  props.padding ? 'panel--padded' : '',
])
</script>

<template>
  <div :class="classes">
    <slot />
  </div>
</template>
