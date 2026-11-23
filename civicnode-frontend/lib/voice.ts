import en from "@/locales/en.json"
import kok from "@/locales/kok.json"
import mr from "@/locales/mr.json"
import { apiRequest, DEMO_MODE } from "@/lib/api-client"
import type { Language } from "@/types/civic"

const transcriptByLanguage = {
  en: en["claim.transcriptEnglish"],
  kok: kok["claim.transcriptKonkani"],
  mr: mr["claim.transcriptMarathi"],
} satisfies Record<Language, string>

export async function transcribeIncident(audio: Blob, language: Language) {
  if (DEMO_MODE) return { transcript: transcriptByLanguage[language], simulated: true }

  const body = new FormData()
  body.append("audio", audio, "incident-audio.webm")
  body.append("language", language)
  const result = await apiRequest<{ transcript: string }>("/api/voice/transcribe", { method: "POST", body })
  return { ...result, simulated: false }
}
