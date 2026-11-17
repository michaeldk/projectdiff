import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { mount } from '@vue/test-utils'

import { _resetThemeForTests, useTheme } from './useTheme'

describe('useTheme', () => {
  beforeEach(() => {
    _resetThemeForTests()
    document.documentElement.classList.remove('dark')
  })

  afterEach(() => {
    _resetThemeForTests()
    document.documentElement.classList.remove('dark')
    vi.restoreAllMocks()
  })

  function mountTheme() {
    const Comp = defineComponent({
      setup() {
        return useTheme()
      },
      template: '<div />',
    })
    return mount(Comp)
  }

  it('resolves system mode from matchMedia and toggles dark class', async () => {
    const listeners: Array<(e: MediaQueryListEvent) => void> = []
    const mql = {
      matches: true,
      media: '(prefers-color-scheme: dark)',
      addEventListener: (_: string, cb: (e: MediaQueryListEvent) => void) => {
        listeners.push(cb)
      },
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    } as unknown as MediaQueryList

    vi.spyOn(window, 'matchMedia').mockReturnValue(mql)

    const wrapper = mountTheme()
    await nextTick()

    expect(wrapper.vm.mode).toBe('system')
    expect(wrapper.vm.resolved).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    wrapper.vm.setMode('light')
    await nextTick()
    expect(wrapper.vm.resolved).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)

    wrapper.vm.setMode('dark')
    await nextTick()
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    wrapper.unmount()
  })

  it('cycles system → light → dark → system', async () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({
      matches: false,
      media: '(prefers-color-scheme: dark)',
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    } as unknown as MediaQueryList)

    const wrapper = mountTheme()
    expect(wrapper.vm.mode).toBe('system')

    wrapper.vm.cycle()
    expect(wrapper.vm.mode).toBe('light')
    wrapper.vm.cycle()
    expect(wrapper.vm.mode).toBe('dark')
    wrapper.vm.cycle()
    expect(wrapper.vm.mode).toBe('system')

    wrapper.unmount()
  })

  it('follows system preference changes while mode is system', async () => {
    const listeners: Array<(e: MediaQueryListEvent) => void> = []
    const mql = {
      matches: false,
      media: '(prefers-color-scheme: dark)',
      addEventListener: (_: string, cb: (e: MediaQueryListEvent) => void) => {
        listeners.push(cb)
      },
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    } as unknown as MediaQueryList

    vi.spyOn(window, 'matchMedia').mockReturnValue(mql)

    const wrapper = mountTheme()
    await nextTick()
    expect(wrapper.vm.resolved).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)

    listeners[0]?.({ matches: true } as MediaQueryListEvent)
    await nextTick()
    expect(wrapper.vm.resolved).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    wrapper.unmount()
  })
})
