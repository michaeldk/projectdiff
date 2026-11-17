import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import type { ThemeMode } from '@/api/types'

const STORAGE_ORDER: ThemeMode[] = ['system', 'light', 'dark']

const mode = ref<ThemeMode>('system')
const systemDark = ref(false)

let media: MediaQueryList | null = null
let mediaHandler: ((event: MediaQueryListEvent) => void) | null = null
let listenerCount = 0

function readSystemDark(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function applyDarkClass(dark: boolean): void {
  if (typeof document === 'undefined') return
  document.documentElement.classList.toggle('dark', dark)
}

function ensureMediaListener(): void {
  if (typeof window === 'undefined' || !window.matchMedia) return
  if (media) return
  media = window.matchMedia('(prefers-color-scheme: dark)')
  systemDark.value = media.matches
  mediaHandler = (event: MediaQueryListEvent) => {
    systemDark.value = event.matches
  }
  media.addEventListener('change', mediaHandler)
}

function releaseMediaListener(): void {
  if (!media || !mediaHandler) return
  if (listenerCount > 0) return
  media.removeEventListener('change', mediaHandler)
  media = null
  mediaHandler = null
}

const resolved = computed<'light' | 'dark'>(() => {
  if (mode.value === 'system') {
    return systemDark.value ? 'dark' : 'light'
  }
  return mode.value
})

watch(
  resolved,
  (value) => {
    applyDarkClass(value === 'dark')
  },
  { immediate: true },
)

/**
 * Shared theme mode. Persisted via settings API by the caller;
 * this composable only owns the `dark` class and system preference tracking.
 */
export function useTheme() {
  onMounted(() => {
    listenerCount += 1
    ensureMediaListener()
    systemDark.value = readSystemDark()
  })

  onUnmounted(() => {
    listenerCount = Math.max(0, listenerCount - 1)
    releaseMediaListener()
  })

  function setMode(next: ThemeMode): void {
    mode.value = next
  }

  function cycle(): void {
    const idx = STORAGE_ORDER.indexOf(mode.value)
    const next = STORAGE_ORDER[(idx + 1) % STORAGE_ORDER.length] ?? 'system'
    mode.value = next
  }

  return {
    mode,
    resolved,
    setMode,
    cycle,
  }
}

/** Test helper: reset module state between Vitest cases. */
export function _resetThemeForTests(): void {
  mode.value = 'system'
  systemDark.value = false
  listenerCount = 0
  if (media && mediaHandler) {
    media.removeEventListener('change', mediaHandler)
  }
  media = null
  mediaHandler = null
  applyDarkClass(false)
}
