const configuredBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

export const API_BASE_URL = configuredBaseUrl.replace(/\/$/, "")
export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE !== "false"

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData
  if (!isFormData && !headers.has("Content-Type")) headers.set("Content-Type", "application/json")
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  })
  if (!response.ok) {
    const message = await response.text().catch(() => "")
    throw new ApiError(message || `Backend request failed (${response.status})`, response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
