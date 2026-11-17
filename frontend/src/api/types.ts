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
}

export type ApplyData = {
  files: string[]
}

export const ErrorCode = {
  NOT_A_REPO: 'NOT_A_REPO',
  TARGET_DIRTY: 'TARGET_DIRTY',
  APPLY_CHECK_FAILED: 'APPLY_CHECK_FAILED',
  STALE_DIFF: 'STALE_DIFF',
  INTERNAL: 'INTERNAL',
} as const

export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode]
