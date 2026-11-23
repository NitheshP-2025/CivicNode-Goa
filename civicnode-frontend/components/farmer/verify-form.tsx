"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { ArrowLeft, ArrowRight, CheckCircle2, LockKeyhole, ShieldCheck, Smartphone } from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { Brand, SiteHeader } from "@/components/shared/site-header"
import { Input } from "@/components/ui/input"
import { useCivic } from "@/hooks/use-civic"
import { useT } from "@/hooks/use-translations"
import { DEMO_MODE } from "@/lib/api-client"
import { DEMO_OTP, sendOtp, verifyOtp } from "@/lib/auth"

const verifySchema = z.object({
  phone: z.string().regex(/^[6-9]\d{9}$/),
  otp: z.string().regex(/^\d{6}$/),
})
type VerifyValues = z.infer<typeof verifySchema>

export function VerifyForm() {
  const t = useT()
  const router = useRouter()
  const { setVerifiedPhone, notify, verifiedPhone } = useCivic()
  const [sent, setSent] = useState(false)
  const [seconds, setSeconds] = useState(30)
  const [error, setError] = useState("")
  const form = useForm<VerifyValues>({
    resolver: zodResolver(verifySchema),
    defaultValues: { phone: verifiedPhone, otp: "" },
    mode: "onTouched",
  })

  useEffect(() => {
    if (verifiedPhone) form.setValue("phone", verifiedPhone)
  }, [form, verifiedPhone])

  useEffect(() => {
    if (!sent || seconds <= 0) return
    const timer = window.setInterval(() => setSeconds((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [sent, seconds])

  async function sendCode() {
    setError("")
    const valid = await form.trigger("phone")
    if (!valid) return
    try {
      const result = await sendOtp(form.getValues("phone"))
      setSent(true)
      setSeconds(30)
      notify(result.simulated ? t("verify.demoCodeReady", { code: DEMO_OTP }) : t("verify.otpSent"))
    } catch {
      setError(t("verify.deliveryError"))
    }
  }

  async function verifyCode(values: VerifyValues) {
    setError("")
    if (!sent) {
      setError(t("verify.sendFirst"))
      return
    }
    try {
      const phone = await verifyOtp(values.phone, values.otp)
      setVerifiedPhone(phone)
      notify(t("verify.verified"))
      router.push("/claim")
    } catch {
      setError(DEMO_MODE ? t("verify.invalid") : t("verify.invalidCode"))
    }
  }

  const benefits = [
    { icon: ShieldCheck, title: t("verify.privacyTitle"), body: t("verify.privacyBody") },
    { icon: LockKeyhole, title: t("verify.accountableTitle"), body: t("verify.accountableBody") },
  ]

  return (
    <div className="min-h-screen bg-[#f7faf8]">
      <SiteHeader active="farmer" />
      <main className="app-container grid min-h-[calc(100vh-77px)] items-center gap-12 py-10 lg:grid-cols-[1fr_.82fr]">
        <div className="hidden max-w-lg lg:block">
          <div className="eyebrow">{t("verify.eyebrow")}</div>
          <h1 className="mt-5 text-5xl font-semibold leading-[1.04] tracking-[-.06em] text-[#173b28]">{t("verify.promoTitle")}</h1>
          <p className="mt-5 text-base leading-8 text-slate-500">{t("verify.promoBody")}</p>
          <div className="mt-8 flex flex-col gap-4">
            {benefits.map(({ icon: Icon, title, body }) => (
              <div key={title} className="flex items-start gap-3">
                <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-[#e5f4e9] text-[#176534]"><Icon className="size-4" /></span>
                <div><div className="text-sm font-bold text-slate-800">{title}</div><div className="mt-1 text-xs leading-5 text-slate-500">{body}</div></div>
              </div>
            ))}
          </div>
        </div>
        <section className="surface mx-auto w-full max-w-[500px] p-6 sm:p-9">
          <Link href="/" className="mb-7 inline-flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-[#14532d]"><ArrowLeft className="size-4" />{t("nav.home")}</Link>
          <div className="mb-7 flex items-center gap-3"><span className="grid size-11 place-items-center rounded-xl bg-[#e6f4e9] text-[#14532d]"><Smartphone className="size-5" /></span><div><div className="text-[10px] font-bold uppercase tracking-[.15em] text-[#728177]">{DEMO_MODE ? t("verify.simulated") : t("verify.secure")}</div><h2 className="mt-1 text-2xl font-semibold tracking-[-.04em] text-[#173b28]">{t("verify.title")}</h2></div></div>
          <p className="mb-7 text-sm leading-6 text-slate-500">{t("verify.body")}</p>
          <form onSubmit={form.handleSubmit(verifyCode)} className="flex flex-col gap-5" noValidate>
            <div>
              <label htmlFor="phone" className="field-label">{t("verify.phone")}</label>
              <div className="flex gap-2"><div className="flex h-11 items-center rounded-lg border border-[#dbe4de] bg-[#f8faf9] px-3 text-sm font-semibold text-slate-500">+91</div><Input id="phone" type="tel" inputMode="numeric" autoComplete="tel-national" maxLength={10} aria-invalid={!!form.formState.errors.phone} className="h-11 rounded-lg border-[#dbe4de]" {...form.register("phone")} /></div>
              {form.formState.errors.phone && <p className="mt-1 text-xs text-red-600" role="alert">{t("verify.invalidPhone")}</p>}
            </div>
            {!sent ? <button type="button" onClick={sendCode} disabled={form.formState.isSubmitting} className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[#14532d] px-4 text-sm font-bold text-white transition hover:bg-[#166534] disabled:opacity-60"><ShieldCheck className="size-4" />{DEMO_MODE ? t("verify.send") : t("verify.sendLive")}</button> : <div className="rounded-xl border border-[#cde8d4] bg-[#f0faf2] p-3 text-xs leading-5 text-[#29613a]">{DEMO_MODE ? t("verify.demo") : t("verify.otpSent")}</div>}
            {sent && <div>
              <label htmlFor="otp" className="field-label">{t("verify.code")}</label>
              <Input id="otp" type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6} placeholder="· · · · · ·" aria-invalid={!!form.formState.errors.otp} className="h-12 rounded-lg text-center font-mono text-lg tracking-[.45em]" {...form.register("otp")} />
              {form.formState.errors.otp && <p className="mt-1 text-xs text-red-600" role="alert">{t("verify.invalidCode")}</p>}
              <div className="mt-3 flex items-center justify-between text-xs text-slate-500"><span>{DEMO_MODE ? t("verify.simulated") : t("verify.secure")}</span><button type="button" onClick={sendCode} disabled={seconds > 0 || form.formState.isSubmitting} className="font-semibold text-[#176534] disabled:cursor-not-allowed disabled:text-slate-400">{seconds > 0 ? `${t("verify.resend")} · 0:${String(seconds).padStart(2, "0")}` : t("verify.resend")}</button></div>
            </div>}
            {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</div>}
            {sent && <button type="submit" disabled={form.formState.isSubmitting} className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-[#14532d] px-4 text-sm font-bold text-white transition hover:bg-[#166534] disabled:opacity-60">{form.formState.isSubmitting ? t("common.loading") : t("verify.confirm")}<ArrowRight className="size-4" /></button>}
          </form>
          <div className="mt-7 flex items-start gap-2 border-t border-[#e7eee8] pt-5 text-[11px] leading-5 text-slate-500"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-[#25814a]" />{DEMO_MODE ? t("verify.demo") : t("verify.privacyBody")}</div>
          <div className="mt-6 flex justify-center"><Brand /></div>
        </section>
      </main>
    </div>
  )
}
