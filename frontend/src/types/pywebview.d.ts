import type { BridgeResult } from '@/api/types'

export interface PywebviewApi {
  ping(): BridgeResult<string>
}

declare global {
  interface Window {
  pywebview?: {
    api?: PywebviewApi
  }
  }
}

export {}