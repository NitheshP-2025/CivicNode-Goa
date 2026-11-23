import { Badge } from "@/components/ui/badge"
import type { CivicClaim, RecommendationLane } from "@/types/civic"

const laneClasses: Record<RecommendationLane, string> = {
  green: "border-[#bde4c7] bg-[#e6f6e9] text-[#176534]",
  amber: "border-[#f3dfb3] bg-[#fff5df] text-[#936000]",
  red: "border-[#f2c4c0] bg-[#fff0ef] text-[#b42318]",
}

export function LaneBadge({ lane, label }: { lane: RecommendationLane; label?: string }) {
  return <Badge variant="outline" className={`rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-[.11em] ${laneClasses[lane]}`}>{label ?? `${lane} lane`}</Badge>
}

const statusClasses: Record<CivicClaim["status"], string> = {
  Submitted: "border-slate-200 bg-slate-50 text-slate-600",
  "Under Verification": "border-sky-200 bg-sky-50 text-sky-700",
  "Awaiting Information": "border-amber-200 bg-amber-50 text-amber-700",
  "Field Inspection Required": "border-orange-200 bg-orange-50 text-orange-700",
  "Under Officer Review": "border-violet-200 bg-violet-50 text-violet-700",
  Approved: "border-emerald-200 bg-emerald-50 text-emerald-700",
  Rejected: "border-rose-200 bg-rose-50 text-rose-700",
  "Payment Processing": "border-teal-200 bg-teal-50 text-teal-700",
  Paid: "border-green-200 bg-green-50 text-green-700",
}

export function StatusBadge({ status }: { status: CivicClaim["status"] }) {
  return <Badge variant="outline" className={`whitespace-nowrap rounded-full px-2.5 py-1 text-[10px] font-bold ${statusClasses[status]}`}>{status}</Badge>
}
