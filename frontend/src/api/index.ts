import type { BridgeResult } from './types'

function getApi() {
  const api = window.pywebview?.api
  if (!api) {
    throw new Error('pywebview API is not available')
  }
  return api
}

export async function ping(): Promise<BridgeResult<string>> {
  return getApi().ping()
}