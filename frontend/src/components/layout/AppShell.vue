<script setup lang="ts">
defineProps<{
  title?: string
}>()
</script>

<template>
  <div class="flex min-h-screen flex-col bg-surface text-fg">
    <header class="flex items-center gap-3 border-b border-border px-4 py-2">
      <h1 class="text-base font-semibold">{{ title ?? 'Project Diff' }}</h1>
      <div class="ml-auto flex items-center gap-2">
        <slot name="header-actions" />
      </div>
    </header>

    <div class="flex min-h-0 flex-1">
      <aside
        v-if="$slots.sidebar"
        class="w-72 shrink-0 overflow-auto border-r border-border bg-surface-muted/40"
      >
        <slot name="sidebar" />
      </aside>
      <main class="min-w-0 flex-1 overflow-auto">
        <slot />
      </main>
    </div>

    <footer v-if="$slots.footer" class="border-t border-border">
      <slot name="footer" />
    </footer>
  </div>
</template>
