"use client"

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import type { CivicClaim, ClaimDraft, DemoRule, Language, DecisionInput } from "@/types/civic"
import { DEMO_MODE } from "@/lib/api-client"
import { listClaims, recordOfficerDecision, submitClaim } from "@/lib/claims"
import { listRules, persistRules } from "@/lib/rules"
import { loadMockState, saveDemoPreferences, defaultRules } from "@/lib/mock-data"

interface CivicContextValue {
  claims: CivicClaim[]
  rules: DemoRule[]
  language: Language
  verifiedPhone: string
  isReady: boolean
  isDemo: boolean
  notice: string
  setLanguage: (language: Language) => void
  setVerifiedPhone: (phone: string) => void
  saveRules: (rules: DemoRule[]) => Promise<void>
  addClaim: (draft: ClaimDraft) => Promise<CivicClaim>
  decide: (id: string, input: DecisionInput) => Promise<CivicClaim>
  notify: (message: string) => void
}

const CivicContext = createContext<CivicContextValue | null>(null)

export function CivicProvider({ children }: { children: React.ReactNode }) {
  const [claims, setClaims] = useState<CivicClaim[]>([])
  const [rules, setRules] = useState<DemoRule[]>(defaultRules)
  const [language, setLanguageState] = useState<Language>("en")
  const [verifiedPhone, setVerifiedPhoneState] = useState("")
  const [isReady, setIsReady] = useState(false)
  const [notice, setNotice] = useState("")

  useEffect(() => {
    let mounted = true
    Promise.all([listClaims(), listRules(), Promise.resolve(loadMockState())]).then(([loadedClaims, loadedRules, stored]) => {
      if (!mounted) return
      setClaims(loadedClaims)
      setRules(loadedRules)
      setLanguageState(stored.language)
      setVerifiedPhoneState(stored.verifiedPhone)
      setIsReady(true)
    }).catch(() => {
      if (!mounted) return
      if (DEMO_MODE) {
        const fallback = loadMockState()
        setClaims(fallback.claims)
        setRules(fallback.rules)
      } else {
        setClaims([])
        setRules(defaultRules)
        setNotice("Central backend unavailable. Live claim data could not be loaded.")
      }
      setIsReady(true)
    })
    const onStorage = (event: StorageEvent) => {
      if (!event.key || event.key === "civicnode-go-demo-v1") {
        const state = loadMockState()
        if (DEMO_MODE) {
          setClaims(state.claims)
          setRules(state.rules)
          setVerifiedPhoneState(state.verifiedPhone)
        }
        setLanguageState(state.language)
      }
    }
    window.addEventListener("storage", onStorage)
    return () => {
      mounted = false
      window.removeEventListener("storage", onStorage)
    }
  }, [])

  useEffect(() => {
    document.documentElement.lang = language === "mr" ? "mr" : language === "kok" ? "kok" : "en"
  }, [language])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(""), 4200)
    return () => window.clearTimeout(timer)
  }, [notice])

  const notify = useCallback((message: string) => setNotice(message), [])
  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next)
    saveDemoPreferences({ language: next })
  }, [])
  const setVerifiedPhone = useCallback((phone: string) => {
    setVerifiedPhoneState(phone)
    if (DEMO_MODE) saveDemoPreferences({ verifiedPhone: phone })
  }, [])
  const saveRules = useCallback(async (next: DemoRule[]) => {
    await persistRules(next)
    setRules(next)
  }, [])
  const addClaim = useCallback(async (draft: ClaimDraft) => {
    const claim = await submitClaim(draft)
    setClaims((previous) => [claim, ...previous.filter((item) => item.id !== claim.id)])
    return claim
  }, [])
  const decide = useCallback(async (id: string, input: DecisionInput) => {
    const claim = await recordOfficerDecision(id, input)
    setClaims((previous) => previous.map((item) => item.id === claim.id ? claim : item))
    return claim
  }, [])

  const value = useMemo(() => ({
    claims, rules, language, verifiedPhone, isReady, isDemo: DEMO_MODE, notice,
    setLanguage, setVerifiedPhone, saveRules, addClaim, decide, notify,
  }), [claims, rules, language, verifiedPhone, isReady, notice, setLanguage, setVerifiedPhone, saveRules, addClaim, decide, notify])

  return (
    <CivicContext.Provider value={value}>
      {children}
      <div className="toast-region" aria-live="polite" aria-atomic="true">
        {notice ? <div className="toast-card">{notice}</div> : null}
      </div>
    </CivicContext.Provider>
  )
}

export function useCivic() {
  const value = useContext(CivicContext)
  if (!value) throw new Error("useCivic must be used within CivicProvider")
  return value
}
