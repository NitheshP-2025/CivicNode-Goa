import type { CivicClaim } from "@/types/civic"
import { listClaims } from "@/lib/claims"

export async function listCases(): Promise<CivicClaim[]> {
  return listClaims()
}

export function getCaseById(claims: CivicClaim[], id: string) {
  return claims.find((claim) => claim.id === id)
}
