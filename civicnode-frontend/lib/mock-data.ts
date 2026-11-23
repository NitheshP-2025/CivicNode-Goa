import type { CivicClaim, ClaimDraft, ClaimStatus, DemoRule, DemoState, DecisionInput } from "@/types/civic"

const STORAGE_KEY = "civicnode-go-demo-v1"
const statuses: ClaimStatus[] = ["Submitted", "Under Verification", "Awaiting Information", "Field Inspection Required", "Under Officer Review", "Approved", "Rejected", "Payment Processing", "Paid"]
const talukas = ["Ponda", "Bicholim", "Sanguem", "Quepem", "Canacona", "Bardez", "Salcete", "Tiswadi"]
const farmers = ["Ramesh Naik", "Laxmi Kamat", "Suresh Gaonkar", "Anita Dessai", "Vishwas Shet", "Maya Parsekar", "Dinesh Sawant", "Kavita Naik"]
const officers = ["Priya Naik", "A. Fernandes", "M. Kamat", "S. Desai"]

export const defaultRules: DemoRule[] = [
  {
    scheme: "Flood Relief",
    version: "DEMO-2026.04",
    effectiveDate: "2026-06-01",
    conditions: ["Applicant identity is verified", "Land record ownership is matched", "Incident is within the notified period", "Officer confirms crop damage in the field"],
    compensationRate: 9800,
    baseLandRate: 0,
    structureAllowance: 0,
    treeAllowance: 0,
    solatiumPercent: 0,
    interestPercent: 0,
    status: "Active",
    sourceLabel: "Illustrative demonstration rule set — not government policy",
  },
  {
    scheme: "Land Acquisition",
    version: "DEMO-2026.02",
    effectiveDate: "2026-04-15",
    conditions: ["Ownership is confirmed in the registry", "Acquisition notice is present", "Asset inventory is officer-verified"],
    compensationRate: 0,
    baseLandRate: 240000,
    structureAllowance: 120000,
    treeAllowance: 18000,
    solatiumPercent: 100,
    interestPercent: 12,
    status: "Active",
    sourceLabel: "Illustrative demonstration rule set — not government policy",
  },
]

function buildClaim(index: number): CivicClaim {
  const id = `CG-2026-${String(index).padStart(3, "0")}`
  const taluka = talukas[(index - 1) % talukas.length]
  const landArea = Number((1 + ((index * 7) % 40) / 10).toFixed(1))
  const scheme = index % 11 === 0 ? "Land Acquisition" : "Flood Relief"
  const status = statuses[(index * 5 + 1) % statuses.length]
  const lane = index % 7 === 0 ? "red" : index % 3 === 0 ? "amber" : "green"
  const normallyWet = index % 17 === 0
  const duplicateRisk = index % 19 === 0 ? "possible" : "none"
  const date = new Date(Date.UTC(2026, 6 + ((index * 3) % 4), 1 + ((index * 7) % 26))).toISOString().slice(0, 10)
  return {
    id,
    farmerName: farmers[(index - 1) % farmers.length],
    phone: `9${String(100000000 + index * 137).slice(0, 9)}`,
    district: "North Goa",
    taluka,
    village: ["Keri", "Bandora", "Curti", "Durbhat", "Mardol"][index % 5],
    surveyNumber: `${100 + index}/${1 + (index % 6)}`,
    subdivision: String(index % 3 + 1),
    landArea,
    areaUnit: "hectares",
    ownership: "Owner cultivator",
    scheme,
    claimType: scheme === "Flood Relief" ? "Crop loss — flooding" : "Land acquisition",
    incidentDate: date,
    incidentLocation: `${taluka}, Goa`,
    incidentDescription: "Heavy monsoon rainfall affected the cultivated plot. Field assessment is pending.",
    reliefRequested: Math.round(landArea * 9800),
    documents: ["Form I & XIV.pdf", "Land ownership record.pdf"],
    status,
    recommendation: lane,
    recommendationReasons: lane === "green" ? ["Registry fields align", "Flood indication present", "No duplicate signal"] : lane === "amber" ? ["Additional evidence requires review", "One field has lower OCR confidence"] : ["A mismatch or duplicate signal requires review"],
    submittedAt: `${date}T09:30:00.000Z`,
    assignedOfficer: officers[(index - 1) % officers.length],
    compensation: scheme === "Flood Relief" ? Math.round(landArea * 9800) : Math.round(landArea * 240000 + 120000),
    floodIndicated: index % 8 !== 0,
    floodEvidenceDate: date,
    normallyWet,
    duplicateRisk,
    duplicateMatches: duplicateRisk === "possible" ? [`CG-2025-${String(index).padStart(3, "0")}`] : [],
    ruleVersion: scheme === "Flood Relief" ? "DEMO-2026.04" : "DEMO-2026.02",
    activity: [{ label: "Claim submitted", detail: "Application entered into the demonstration pipeline.", at: `${date}T09:30:00.000Z` }],
  }
}

export function createSeedClaims(): CivicClaim[] {
  const claims = Array.from({ length: 180 }, (_, index) => buildClaim(index + 1))
  claims[0] = {
    ...claims[0],
    id: "CG-2026-001",
    farmerName: "Ramesh Naik",
    phone: "9876543210",
    taluka: "Ponda",
    village: "Bandora",
    surveyNumber: "123/4",
    subdivision: "2",
    landArea: 2.5,
    areaUnit: "hectares",
    scheme: "Flood Relief",
    claimType: "Crop loss — flooding",
    incidentDate: "2026-07-18",
    incidentLocation: "Bandora, Ponda",
    status: "Under Officer Review",
    recommendation: "green",
    recommendationReasons: ["Extracted document fields match the registry", "Flood indication is present for the incident date", "No duplicate claim was detected"],
    submittedAt: "2026-07-19T10:18:00.000Z",
    assignedOfficer: "Priya Naik",
    compensation: 24500,
    reliefRequested: 24500,
    floodIndicated: true,
    floodEvidenceDate: "2026-07-18",
    normallyWet: false,
    duplicateRisk: "none",
    duplicateMatches: [],
    ruleVersion: "DEMO-2026.04",
    documents: ["Form I & XIV.pdf", "Land ownership record.pdf", "Crop loss statement.jpg"],
    activity: [
      { label: "Claim submitted", detail: "Application received through the farmer portal.", at: "2026-07-19T10:18:00.000Z" },
      { label: "Document verification", detail: "Synthetic document fields extracted for demonstration.", at: "2026-07-19T10:19:00.000Z" },
      { label: "Registry comparison", detail: "Owner, survey, area and village align in the demo registry.", at: "2026-07-19T10:20:00.000Z" },
      { label: "Flood evidence assessment", detail: "Satellite layer indicates water coverage; damage remains for officer confirmation.", at: "2026-07-19T10:21:00.000Z" },
      { label: "Compensation calculation", detail: "2.5 ha × ₹9,800 per hectare = ₹24,500.", at: "2026-07-19T10:22:00.000Z" },
    ],
  }
  return claims
}

const initialState = (): DemoState => ({
  claims: createSeedClaims(),
  rules: defaultRules,
  language: "en",
  verifiedPhone: "",
})

export function readDemoState(): DemoState {
  if (typeof window === "undefined") return initialState()
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (!stored) return initialState()
    const parsed = JSON.parse(stored) as Partial<DemoState>
    return {
      claims: Array.isArray(parsed.claims) && parsed.claims.length ? parsed.claims : createSeedClaims(),
      rules: Array.isArray(parsed.rules) && parsed.rules.length ? parsed.rules : defaultRules,
      language: parsed.language === "kok" || parsed.language === "mr" ? parsed.language : "en",
      verifiedPhone: typeof parsed.verifiedPhone === "string" ? parsed.verifiedPhone : "",
    }
  } catch {
    return initialState()
  }
}

function writeState(state: DemoState) {
  if (typeof window !== "undefined") window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

export function saveDemoPreferences(patch: Partial<Pick<DemoState, "language" | "verifiedPhone" | "rules">>) {
  const state = readDemoState()
  writeState({ ...state, ...patch })
}

export function listMockClaims() {
  return readDemoState().claims
}

export function createMockClaim(draft: ClaimDraft): CivicClaim {
  const state = readDemoState()
  const nextNumber = Math.max(180, ...state.claims.map((claim) => Number(claim.id.split("-").at(-1)) || 0)) + 1
  const id = `CG-2026-${String(nextNumber).padStart(3, "0")}`
  const rule = state.rules.find((item) => item.scheme === draft.scheme) ?? defaultRules[0]
  const area = draft.areaUnit === "acres" ? draft.landArea * 0.404686 : draft.landArea
  const compensation = draft.scheme === "Flood Relief" ? Math.round(area * rule.compensationRate) : Math.round(area * rule.baseLandRate + rule.structureAllowance)
  const claim: CivicClaim = {
    ...draft,
    id,
    status: "Submitted",
    recommendation: "amber",
    recommendationReasons: ["Documents are queued for verification", "Officer confirmation is required before a decision"],
    submittedAt: new Date().toISOString(),
    assignedOfficer: "Unassigned",
    compensation,
    floodIndicated: false,
    floodEvidenceDate: draft.incidentDate,
    normallyWet: false,
    duplicateRisk: "none",
    duplicateMatches: [],
    ruleVersion: rule.version,
    activity: [{ label: "Claim submitted", detail: "Claim received in demonstration mode. AI recommendations do not make decisions.", at: new Date().toISOString() }],
  }
  writeState({ ...state, claims: [claim, ...state.claims] })
  return claim
}

export function applyMockDecision(id: string, input: DecisionInput): CivicClaim | undefined {
  const state = readDemoState()
  const claim = state.claims.find((item) => item.id === id)
  if (!claim) return undefined
  const statusByAction = {
    approve: "Approved",
    "request-info": "Awaiting Information",
    "field-inspection": "Field Inspection Required",
    reject: "Rejected",
  } as const
  const labels = {
    approve: "Officer approved claim",
    "request-info": "More information requested",
    "field-inspection": "Field inspection requested",
    reject: "Officer rejected claim",
  } as const
  const now = new Date().toISOString()
  const updated: CivicClaim = {
    ...claim,
    status: statusByAction[input.action],
    decision: { ...input, officer: "Priya Naik", decidedAt: now },
    activity: [...claim.activity, { label: labels[input.action], detail: input.remarks || "Decision recorded by the reviewing officer.", at: now }],
  }
  writeState({ ...state, claims: state.claims.map((item) => item.id === id ? updated : item) })
  return updated
}

export function saveMockRules(rules: DemoRule[]) {
  const state = readDemoState()
  writeState({ ...state, rules })
}

export function verifyMockPhone(phone: string) {
  const state = readDemoState()
  writeState({ ...state, verifiedPhone: phone })
}

export function loadMockState() {
  return readDemoState()
}
