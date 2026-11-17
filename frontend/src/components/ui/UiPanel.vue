<script setup lang="ts">
withDefaults(
  defineProps<{
    padding?: boolean
  }>(),
  { padding: true },
)
</script>

<template>
  <div class="rounded-lg border border-border bg-surface" :class="padding ? 'p-4' : ''">
    <slot />
  </div>
</template>
