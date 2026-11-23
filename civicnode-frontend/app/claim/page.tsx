import type { Metadata } from "next"
import { ClaimWizard } from "@/components/farmer/claim-wizard"

export const metadata: Metadata = { title: "Apply for relief" }

export default function ClaimPage() {
  return <ClaimWizard />
}
