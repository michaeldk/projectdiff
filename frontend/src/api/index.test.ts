import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  apply,
  computeDiff,
  createProject,
  deleteProject,
  getSettings,
  listProjects,
  pickFolder,
  ping,
  saveSettings,
  updateProject,
} from './index'

describe('api wrapper', () => {
  afterEach(() => {
    delete (window as Window & { pywebview?: unknown }).pywebview
  })

  it('throws when pywebview is missing', async () => {
    await expect(ping()).rejects.toThrow('pywebview API is not available')
  })

  it('calls ping', async () => {
    const pingMock = vi.fn().mockResolvedValue({ ok: true, data: 'pong' })
    window.pywebview = { api: { ping: pingMock } as never }

    const result = await ping()
    expect(pingMock).toHaveBeenCalledOnce()
    expect(result).toEqual({ ok: true, data: 'pong' })
  })

  it('passes through structured bridge errors', async () => {
    const applyMock = vi.fn().mockResolvedValue({
      ok: false,
      error: { code: 'APPLY_CHECK_FAILED', message: 'patch does not apply' },
    })
    window.pywebview = { api: { apply: applyMock } as never }

    await expect(apply('x', ['0:0:1'])).resolves.toEqual({
      ok: false,
      error: { code: 'APPLY_CHECK_FAILED', message: 'patch does not apply' },
    })
  })

  it('calls pick_folder, get/save settings, compute_diff, and apply', async () => {
    const pickMock = vi
      .fn()
      .mockResolvedValue({ ok: true, data: { side: 'a', path: 'C:/repo' } })
    const getMock = vi
      .fn()
      .mockResolvedValue({ ok: true, data: { excludes: ['dist/'], theme: 'system' } })
    const saveMock = vi
      .fn()
      .mockResolvedValue({ ok: true, data: { excludes: ['dist/'], theme: 'dark' } })
    const diffMock = vi.fn().mockResolvedValue({
      ok: true,
      data: {
        file_list: [{ path: 'a.ts', side: 'both', binary: false }],
        diff: { diff_id: 'x', files: [] },
        destination_dirty: false,
      },
    })
    const applyMock = vi.fn().mockResolvedValue({ ok: true, data: { files: ['a.ts'] } })

    window.pywebview = {
      api: {
        pick_folder: pickMock,
        get_settings: getMock,
        save_settings: saveMock,
        compute_diff: diffMock,
        apply: applyMock,
      } as never,
    }

    await expect(pickFolder('a')).resolves.toEqual({
      ok: true,
      data: { side: 'a', path: 'C:/repo' },
    })
    expect(pickMock).toHaveBeenCalledWith('a')

    await expect(getSettings()).resolves.toMatchObject({ ok: true })
    expect(getMock).toHaveBeenCalledOnce()

    await expect(saveSettings({ theme: 'dark' })).resolves.toMatchObject({ ok: true })
    expect(saveMock).toHaveBeenCalledWith({ theme: 'dark' })

    await expect(computeDiff('/a', '/b')).resolves.toMatchObject({ ok: true })
    expect(diffMock).toHaveBeenCalledWith('/a', '/b')

    await expect(apply('x', ['0:0:1'])).resolves.toEqual({
      ok: true,
      data: { files: ['a.ts'] },
    })
    expect(applyMock).toHaveBeenCalledWith('x', ['0:0:1'])
  })

  it('calls project list/create/update/delete', async () => {
    const project = {
      id: 'p1',
      name: 'Pair',
      path_a: 'C:/a',
      path_b: 'C:/b',
      created_at: '2024-01-01T00:00:00+00:00',
      updated_at: '2024-01-01T00:00:00+00:00',
    }
    const listMock = vi.fn().mockResolvedValue({ ok: true, data: [project] })
    const createMock = vi.fn().mockResolvedValue({ ok: true, data: project })
    const updateMock = vi
      .fn()
      .mockResolvedValue({ ok: true, data: { ...project, name: 'Renamed' } })
    const deleteMock = vi.fn().mockResolvedValue({ ok: true, data: { id: 'p1' } })

    window.pywebview = {
      api: {
        list_projects: listMock,
        create_project: createMock,
        update_project: updateMock,
        delete_project: deleteMock,
      } as never,
    }

    await expect(listProjects()).resolves.toEqual({ ok: true, data: [project] })
    expect(listMock).toHaveBeenCalledOnce()

    await expect(
      createProject({ name: 'Pair', path_a: 'C:/a', path_b: 'C:/b' }),
    ).resolves.toMatchObject({ ok: true })
    expect(createMock).toHaveBeenCalledWith({
      name: 'Pair',
      path_a: 'C:/a',
      path_b: 'C:/b',
    })

    await expect(updateProject({ id: 'p1', name: 'Renamed' })).resolves.toMatchObject({
      ok: true,
      data: { name: 'Renamed' },
    })
    expect(updateMock).toHaveBeenCalledWith({ id: 'p1', name: 'Renamed' })

    await expect(deleteProject('p1')).resolves.toEqual({
      ok: true,
      data: { id: 'p1' },
    })
    expect(deleteMock).toHaveBeenCalledWith('p1')
  })
})
