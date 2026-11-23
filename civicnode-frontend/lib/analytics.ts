import type { CivicClaim } from "@/types/civic"

export function summarizeClaims(claims: CivicClaim[]) {
  const count = (test: (claim: CivicClaim) => boolean) => claims.filter(test).length
  return {
    total: claims.length,
    verified: count((claim) => ["Under Officer Review", "Approved", "Payment Processing", "Paid"].includes(claim.status)),
    approved: count((claim) => ["Approved", "Payment Processing", "Paid"].includes(claim.status)),
    rejected: count((claim) => claim.status === "Rejected"),
    pending: count((claim) => !["Approved", "Rejected", "Paid"].includes(claim.status)),
    compensation: claims.filter((claim) => ["Approved", "Payment Processing", "Paid"].includes(claim.status)).reduce((total, claim) => total + claim.compensation, 0),
    green: count((claim) => claim.recommendation === "green"),
    amber: count((claim) => claim.recommendation === "amber"),
    red: count((claim) => claim.recommendation === "red"),
  }
}

export function getTalukaOptions(claims: CivicClaim[]) {
  return Array.from(new Set(claims.map((claim) => claim.taluka))).sort()
}
