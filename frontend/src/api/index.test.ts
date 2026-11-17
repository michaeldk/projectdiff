import { afterEach, describe, expect, it, vi } from 'vitest'

import { ping } from './index'

describe('api ping', () => {
  afterEach(() => {
    delete (window as Window & { pywebview?: unknown }).pywebview
  })

  it('calls window.pywebview.api.ping', async () => {
    const pingMock = vi.fn().mockReturnValue({ ok: true, data: 'pong' })
    window.pywebview = { api: { ping: pingMock } }

    const result = await ping()
    expect(pingMock).toHaveBeenCalledOnce()
    expect(result).toEqual({ ok: true, data: 'pong' })
  })

  it('throws when pywebview is missing', async () => {
    await expect(ping()).rejects.toThrow('pywebview API is not available')
  })
})