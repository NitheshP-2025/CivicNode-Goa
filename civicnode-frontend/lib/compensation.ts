import type { CivicClaim, DemoRule } from "@/types/civic"

export interface CompensationBreakdown {
  total: number
  formula: string
  rows: { label: string; amount: number; note?: string }[]
}

export function calculateCompensation(claim: CivicClaim, rule?: DemoRule): CompensationBreakdown {
  const rate = rule?.compensationRate ?? 9800
  const areaHa = claim.areaUnit === "acres" ? claim.landArea * 0.404686 : claim.landArea
  if (claim.scheme === "Flood Relief") {
    const total = Math.round(areaHa * rate)
    return {
      total,
      formula: `${areaHa.toFixed(3)} ha × ₹${rate.toLocaleString("en-IN")}/ha`,
      rows: [
        { label: "Eligible land area", amount: areaHa, note: "Hectares (converted from submitted unit where needed)" },
        { label: "Illustrative rate per hectare", amount: rate },
        { label: "Compensation estimate", amount: total },
      ],
    }
  }
  const base = Math.round(areaHa * (rule?.baseLandRate ?? 240000))
  const structures = rule?.structureAllowance ?? 120000
  const trees = rule?.treeAllowance ?? 18000
  const solatium = Math.round((base + structures + trees) * (rule?.solatiumPercent ?? 100) / 100)
  const interest = Math.round(base * (rule?.interestPercent ?? 12) / 100)
  const total = base + structures + trees + solatium + interest
  return {
    total,
    formula: "Base land value + structures + trees + solatium + illustrative interest",
    rows: [
      { label: "Base land value", amount: base, note: `${areaHa.toFixed(3)} ha × ₹${(rule?.baseLandRate ?? 240000).toLocaleString("en-IN")}/ha` },
      { label: "Structures", amount: structures },
      { label: "Trees", amount: trees },
      { label: `Solatium (${rule?.solatiumPercent ?? 100}%)`, amount: solatium },
      { label: `Interest (${rule?.interestPercent ?? 12}%)`, amount: interest },
      { label: "Compensation estimate", amount: total },
    ],
  }
}
