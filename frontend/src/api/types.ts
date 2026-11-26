export type BridgeError = {
  code: string
  message: string
}

/** Bridge success/failure envelope. */
export type Result<T> =
  | { ok: true; data: T }
  | { ok: false; error: BridgeError }

/** @deprecated Prefer `Result<T>`; kept for existing imports. */
export type BridgeResult<T> = Result<T>

export type ThemeMode = 'light' | 'dark' | 'system'

export type Settings = {
  excludes: string[]
  theme: ThemeMode
}

export type PickFolderSide = 'a' | 'b'

export type PickFolderData = {
  side: PickFolderSide
  path: string
}

export type FileEntry = {
  path: string
  side: 'both' | 'only_a' | 'only_b'
  binary: boolean
}

export type ComputeDiffData = {
  file_list: FileEntry[]
  diff: import('@/types/diff').DiffResult
  destination_dirty: boolean
}

export type ApplyData = {
  files: string[]
}

export type Project = {
  id: string
  name: string
  path_a: string
  path_b: string
  created_at: string
  updated_at: string
}

export type CreateProjectPayload = {
  name: string
  path_a: string
  path_b: string
}

export type UpdateProjectPayload = {
  id: string
  name?: string
  path_a?: string
  path_b?: string
}

export type DeleteProjectData = {
  id: string
}

export const ErrorCode = {
  NOT_A_REPO: 'NOT_A_REPO',
  APPLY_CHECK_FAILED: 'APPLY_CHECK_FAILED',
  STALE_DIFF: 'STALE_DIFF',
  NOT_FOUND: 'NOT_FOUND',
  INTERNAL: 'INTERNAL',
} as const

export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode]
