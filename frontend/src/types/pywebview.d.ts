import type {
  ApplyData,
  ComputeDiffData,
  CreateProjectPayload,
  DeleteProjectData,
  PickFolderData,
  PickFolderSide,
  Project,
  Result,
  Settings,
  UpdateProjectPayload,
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
  list_projects(): Promise<Result<Project[]>> | Result<Project[]>
  create_project(
    payload: CreateProjectPayload,
  ): Promise<Result<Project>> | Result<Project>
  update_project(
    payload: UpdateProjectPayload,
  ): Promise<Result<Project>> | Result<Project>
  delete_project(
    projectId: string,
  ): Promise<Result<DeleteProjectData>> | Result<DeleteProjectData>
}

declare global {
  interface Window {
    pywebview?: {
      api?: PywebviewApi
    }
  }
}

export {}
