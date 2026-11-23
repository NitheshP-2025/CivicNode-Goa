import type { CivicClaim, ClaimDraft, DecisionInput } from "@/types/civic"
import { apiRequest, DEMO_MODE } from "@/lib/api-client"
import { applyMockDecision, createMockClaim, listMockClaims } from "@/lib/mock-data"

export async function listClaims(): Promise<CivicClaim[]> {
  return DEMO_MODE ? listMockClaims() : apiRequest<CivicClaim[]>("/api/claims")
}

export async function submitClaim(draft: ClaimDraft): Promise<CivicClaim> {
  return DEMO_MODE
    ? createMockClaim(draft)
    : apiRequest<CivicClaim>("/api/claims", { method: "POST", body: JSON.stringify(draft) })
}

export async function recordOfficerDecision(id: string, input: DecisionInput): Promise<CivicClaim> {
  return DEMO_MODE
    ? applyMockDecision(id, input) ?? Promise.reject(new Error("Claim not found"))
    : apiRequest<CivicClaim>(`/api/claims/${encodeURIComponent(id)}/decision`, { method: "POST", body: JSON.stringify(input) })
}
