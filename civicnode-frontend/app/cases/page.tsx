import type { Metadata } from "next"
import { CaseQueue } from "@/components/officer/case-queue"

export const metadata: Metadata = { title: "Case queue · CivicNode Goa" }

export default function CasesPage() {
  return <CaseQueue />
}
