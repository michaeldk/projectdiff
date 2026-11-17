import type {
  ApplyData,
  ComputeDiffData,
  PickFolderData,
  PickFolderSide,
  Result,
  Settings,
} from '@/api/types'

export interface PywebviewApi {
  ping(): Promise<Result<string>> | Result<string>
  pick_folder(side: PickFolderSide): Promise<Result<PickFolderData | null>> | Result<PickFolderData | null>
  get_settings(): Promise<Result<Settings>> | Result<Settings>
  save_settings(
    payload: Partial<Settings>,
  ): Promise<Result<Settings>> | Result<Settings>
  compute_diff(
    pathA: string,
    pathB: string,
  ): Promise<Result<ComputeDiffData>> | Result<ComputeDiffData>
  apply(
    diffId: string,
    lineIds: string[],
  ): Promise<Result<ApplyData>> | Result<ApplyData>
}

declare global {
  interface Window {
    pywebview?: {
      api?: PywebviewApi
    }
  }
}

export {}
