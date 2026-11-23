import { apiRequest, DEMO_MODE } from "@/lib/api-client"

export interface ClaimDocumentReference {
  fileName: string
  documentId?: string
}

export async function uploadClaimDocuments(files: File[]): Promise<ClaimDocumentReference[]> {
  if (DEMO_MODE) return files.map((file) => ({ fileName: file.name }))

  const body = new FormData()
  for (const file of files) body.append("files", file, file.name)
  const response = await apiRequest<{ documents: ClaimDocumentReference[] }>("/api/claims/documents", {
    method: "POST",
    body,
  })
  return response.documents
}
