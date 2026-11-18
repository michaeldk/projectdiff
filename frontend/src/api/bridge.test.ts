import { afterEach, describe, expect, it, vi } from 'vitest'

import { isBridgeAvailable, waitForBridge } from './bridge'

describe('waitForBridge', () => {
  afterEach(() => {
    delete (window as Window & { pywebview?: unknown }).pywebview
    vi.useRealTimers()
  })

  it('resolves immediately when the api is already present', async () => {
    window.pywebview = { api: { ping: vi.fn() } as never }
    await expect(waitForBridge(100)).resolves.toBe(true)
  })

  it('resolves true when pywebviewready fires with api', async () => {
    const pending = waitForBridge(1000)
    window.pywebview = { api: { ping: vi.fn() } as never }
    window.dispatchEvent(new Event('pywebviewready'))
    await expect(pending).resolves.toBe(true)
  })

  it('resolves false after timeout when api never appears', async () => {
    vi.useFakeTimers()
    const pending = waitForBridge(50)
    await vi.advanceTimersByTimeAsync(50)
    await expect(pending).resolves.toBe(false)
  })

  it('isBridgeAvailable reflects window.pywebview.api', () => {
    expect(isBridgeAvailable()).toBe(false)
    window.pywebview = { api: { ping: vi.fn() } as never }
    expect(isBridgeAvailable()).toBe(true)
  })
})
