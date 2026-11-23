import type { Metadata } from "next"
import { CaseReview } from "@/components/officer/case-review"

export const metadata: Metadata = { title: "Evidence review · CivicNode Goa" }

export default async function CaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <CaseReview id={id} />
}
