export type Language = "en" | "kok" | "mr"
export type RecommendationLane = "green" | "amber" | "red"
export type ClaimStatus =
  | "Submitted"
  | "Under Verification"
  | "Awaiting Information"
  | "Field Inspection Required"
  | "Under Officer Review"
  | "Approved"
  | "Rejected"
  | "Payment Processing"
  | "Paid"
export type DecisionAction = "approve" | "request-info" | "field-inspection" | "reject"

export interface ClaimActivity {
  label: string
  detail: string
  at: string
}

export interface ClaimDocumentReference {
  fileName: string
  documentId?: string
}

export interface ClaimDraft {
  farmerName: string
  phone: string
  district: string
  taluka: string
  village: string
  surveyNumber: string
  subdivision: string
  landArea: number
  areaUnit: "hectares" | "acres"
  ownership: string
  scheme: "Flood Relief" | "Land Acquisition"
  claimType: string
  incidentDate: string
  incidentLocation: string
  incidentDescription: string
  reliefRequested: number
  documents: string[]
  documentRefs?: ClaimDocumentReference[]
  operatorName?: string
  operatorCenter?: string
}

export interface OfficerDecision {
  action: DecisionAction
  remarks: string
  officer: string
  decidedAt: string
}

export interface CivicClaim extends ClaimDraft {
  id: string
  status: ClaimStatus
  recommendation: RecommendationLane
  recommendationReasons: string[]
  submittedAt: string
  assignedOfficer: string
  compensation: number
  floodIndicated: boolean
  floodEvidenceDate: string
  normallyWet: boolean
  duplicateRisk: "none" | "possible" | "confirmed"
  duplicateMatches: string[]
  ruleVersion: string
  activity: ClaimActivity[]
  decision?: OfficerDecision
}

export interface DemoRule {
  scheme: "Flood Relief" | "Land Acquisition"
  version: string
  effectiveDate: string
  conditions: string[]
  compensationRate: number
  baseLandRate: number
  structureAllowance: number
  treeAllowance: number
  solatiumPercent: number
  interestPercent: number
  status: "Active" | "Draft"
  sourceLabel: string
}

export interface DemoState {
  claims: CivicClaim[]
  rules: DemoRule[]
  language: Language
  verifiedPhone: string
}

export interface DecisionInput {
  action: DecisionAction
  remarks: string
}
