import type { Metadata } from "next"
import { VerifyForm } from "@/components/farmer/verify-form"

export const metadata: Metadata = { title: "Mobile verification" }

export default function VerifyPage() {
  return <VerifyForm />
}
