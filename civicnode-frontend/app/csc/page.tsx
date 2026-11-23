import type { Metadata } from "next"
import { ClaimWizard } from "@/components/farmer/claim-wizard"

export const metadata: Metadata = { title: "CSC operator mode" }

export default function CscPage() {
  return <ClaimWizard operatorMode />
}
