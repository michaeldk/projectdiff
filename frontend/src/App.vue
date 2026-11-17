<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { ping } from '@/api'

const bridgeStatus = ref<'idle' | 'loading' | 'ok' | 'error'>('idle')
const bridgeMessage = ref('')

onMounted(async () => {
  if (!window.pywebview?.api) {
    bridgeStatus.value = 'error'
    bridgeMessage.value =
      'Bridge unavailable (open via pywebview or mock in tests). Dev UI still loads.'
    return
  }
  bridgeStatus.value = 'loading'
  try {
    const result = await ping()
    if (result.ok) {
      bridgeStatus.value = 'ok'
      bridgeMessage.value = result.data
    } else {
      bridgeStatus.value = 'error'
      bridgeMessage.value = result.error.message
    }
  } catch (err) {
    bridgeStatus.value = 'error'
    bridgeMessage.value = err instanceof Error ? err.message : String(err)
  }
})
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
    <h1 class="text-2xl font-semibold text-fg">Project Diff</h1>
    <p class="text-fg-muted">Milestone 1 scaffold — compare git repos side by side.</p>
    <div class="panel min-w-72 text-center">
      <p class="text-sm text-fg-muted">Bridge ping</p>
      <p class="mt-1 font-mono text-accent">
        <template v-if="bridgeStatus === 'loading'">…</template>
        <template v-else-if="bridgeStatus === 'ok'">{{ bridgeMessage }}</template>
        <template v-else-if="bridgeStatus === 'error'">{{ bridgeMessage }}</template>
        <template v-else>—</template>
      </p>
    </div>
  </div>
</template>