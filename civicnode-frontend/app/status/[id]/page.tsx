import type { Metadata } from "next"
import { ClaimStatusView } from "@/components/farmer/claim-status-view"

export const metadata: Metadata = { title: "Track your claim" }

export default async function StatusPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <ClaimStatusView id={id} />
}
