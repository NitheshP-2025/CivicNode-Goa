import { apiRequest, DEMO_MODE } from "@/lib/api-client"
import { verifyMockPhone } from "@/lib/mock-data"

export const DEMO_OTP = "123456"

export function normalizePhone(phone: string) {
  const digits = phone.replace(/\D/g, "")
  return digits.length === 12 && digits.startsWith("91") ? digits.slice(2) : digits
}

export function isValidGoaMobile(phone: string) {
  return /^[6-9]\d{9}$/.test(normalizePhone(phone))
}

export async function sendOtp(phone: string) {
  const normalized = normalizePhone(phone)
  if (DEMO_MODE) return { sent: true, simulated: true }
  return apiRequest<{ sent: boolean; simulated?: boolean }>("/api/auth/otp", {
    method: "POST",
    body: JSON.stringify({ phone: normalized }),
  })
}

export async function verifyOtp(phone: string, otp: string) {
  const normalized = normalizePhone(phone)
  if (DEMO_MODE) {
    if (otp !== DEMO_OTP) throw new Error("The demonstration OTP is not correct.")
    verifyMockPhone(normalized)
    return normalized
  }
  const result = await apiRequest<{ verified: boolean; phone: string }>("/api/auth/verify", {
    method: "POST",
    body: JSON.stringify({ phone: normalized, otp }),
  })
  if (!result.verified) throw new Error("The one-time code could not be verified.")
  return result.phone
}
