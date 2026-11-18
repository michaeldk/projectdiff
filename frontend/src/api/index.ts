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
} from './types'

export { isBridgeAvailable, waitForBridge } from './bridge'

function getApi() {
  const api = window.pywebview?.api
  if (!api) {
    throw new Error('pywebview API is not available')
  }
  return api
}

export async function ping(): Promise<Result<string>> {
  return getApi().ping()
}

export async function pickFolder(side: PickFolderSide): Promise<Result<PickFolderData | null>> {
  return getApi().pick_folder(side)
}

export async function getSettings(): Promise<Result<Settings>> {
  return getApi().get_settings()
}

export async function saveSettings(settings: Partial<Settings>): Promise<Result<Settings>> {
  return getApi().save_settings(settings)
}

export async function computeDiff(
  pathA: string,
  pathB: string,
): Promise<Result<ComputeDiffData>> {
  return getApi().compute_diff(pathA, pathB)
}

export async function apply(
  diffId: string,
  lineIds: string[],
): Promise<Result<ApplyData>> {
  return getApi().apply(diffId, lineIds)
}

export async function listProjects(): Promise<Result<Project[]>> {
  return getApi().list_projects()
}

export async function createProject(
  payload: CreateProjectPayload,
): Promise<Result<Project>> {
  return getApi().create_project(payload)
}

export async function updateProject(
  payload: UpdateProjectPayload,
): Promise<Result<Project>> {
  return getApi().update_project(payload)
}

export async function deleteProject(projectId: string): Promise<Result<DeleteProjectData>> {
  return getApi().delete_project(projectId)
}

export type {
  ApplyData,
  BridgeError,
  BridgeResult,
  ComputeDiffData,
  CreateProjectPayload,
  DeleteProjectData,
  ErrorCode,
  FileEntry,
  PickFolderData,
  PickFolderSide,
  Project,
  Result,
  Settings,
  ThemeMode,
  UpdateProjectPayload,
} from './types'
export { ErrorCode as ErrorCodes } from './types'
