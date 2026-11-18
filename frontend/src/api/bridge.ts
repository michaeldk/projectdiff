/** Wait until pywebview injects `window.pywebview.api`, or time out. */

const DEFAULT_TIMEOUT_MS = 5000

export function isBridgeAvailable(): boolean {
  return Boolean(window.pywebview?.api)
}

/**
 * Resolves when the js_api bridge is ready.
 * pywebview fires `pywebviewready` after injecting the API; that often lands
 * after Vue's first `onMounted`, especially with `file://` packaged builds.
 */
export function waitForBridge(timeoutMs = DEFAULT_TIMEOUT_MS): Promise<boolean> {
  if (isBridgeAvailable()) {
    return Promise.resolve(true)
  }

  return new Promise((resolve) => {
    let settled = false

    const finish = (ok: boolean) => {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      window.removeEventListener('pywebviewready', onReady)
      resolve(ok)
    }

    const onReady = () => {
      finish(isBridgeAvailable())
    }

    const timer = window.setTimeout(() => {
      finish(isBridgeAvailable())
    }, timeoutMs)

    window.addEventListener('pywebviewready', onReady, { once: true })
  })
}
