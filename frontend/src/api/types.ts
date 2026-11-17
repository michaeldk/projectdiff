export type BridgeError = {
  code: string
  message: string
}

export type BridgeResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: BridgeError }