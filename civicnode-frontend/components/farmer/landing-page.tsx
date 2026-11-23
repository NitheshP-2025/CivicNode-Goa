"use client"

import Image from "next/image"
import Link from "next/link"
import { motion } from "framer-motion"
import { ArrowDownRight, ArrowRight, ArrowUpRight, BadgeCheck, Check, CircleHelp, FileCheck2, Languages, MapPinned, ShieldCheck, Sparkles, UsersRound, WalletCards, Waves } from "lucide-react"
import { SiteHeader } from "@/components/shared/site-header"
import { useT } from "@/hooks/use-translations"
import { useCivic } from "@/hooks/use-civic"
import { formatINR } from "@/lib/format"

const flowIcons = [FileCheck2, BadgeCheck, Waves, ShieldCheck]
const flowKeys = ["steps.submit", "steps.verify", "steps.assess", "steps.decide"] as const
const flowDetailKeys = ["landing.step1", "landing.step2", "landing.step3", "landing.step4"] as const

export function LandingPage() {
  const t = useT()
  const { claims, rules } = useCivic()
  const demoClaim = claims.find((claim) => claim.id === "CG-2026-001")
  const floodRule = rules.find((rule) => rule.scheme === "Flood Relief")
  const acquisitionRule = rules.find((rule) => rule.scheme === "Land Acquisition")
  const schemeName = demoClaim?.scheme === "Land Acquisition" ? t("claim.landAcquisition") : t("claim.floodRelief")
  const statusName = demoClaim?.status === "Under Officer Review" ? t("status.statusOfficerReview") : t("status.statusSubmitted")
  const laneName = demoClaim?.recommendation === "amber" ? t("status.laneAmber") : demoClaim?.recommendation === "red" ? t("status.laneRed") : t("status.laneGreen")
  const evidenceDate = demoClaim?.floodEvidenceDate ? new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric" }).format(new Date(demoClaim.floodEvidenceDate)) : ""
  const hectares = demoClaim ? (demoClaim.areaUnit === "acres" ? demoClaim.landArea * 0.404686 : demoClaim.landArea) : 0
  const claimLink = demoClaim ? `/status/${demoClaim.id}` : "/verify"

  return (
    <div className="overflow-hidden bg-[#f8faf9]">
      <SiteHeader active="farmer" />
      <main>
        <section className="relative isolate overflow-hidden border-b border-[#e8efea] bg-[radial-gradient(ellipse_at_5%_0%,rgba(220,252,231,.9),transparent_38%),linear-gradient(180deg,#fbfdfb_0%,#f5f8f5_100%)]">
          <div className="app-container grid min-h-[620px] items-center gap-10 py-14 lg:grid-cols-[.88fr_1.12fr] lg:py-20">
            <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .55 }} className="relative z-10 max-w-[570px]">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#d7eadc] bg-white/85 px-3 py-1.5 text-[11px] font-bold text-[#28633d] shadow-sm">
                <span className="relative flex size-2"><span className="absolute inline-flex size-full animate-ping rounded-full bg-[#16a34a] opacity-40" /><span className="relative inline-flex size-2 rounded-full bg-[#16a34a]" /></span>
                {t("hero.eyebrow")}
              </div>
              <h1 className="max-w-[650px] text-[clamp(3.35rem,6.8vw,6.2rem)] font-semibold leading-[.97] tracking-[-.075em] text-[#173b28]">{t("hero.title")}</h1>
              <p className="mt-7 max-w-[500px] text-base leading-7 text-[#607066] sm:text-lg sm:leading-8">{t("hero.body")}</p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href="/verify" className="inline-flex h-12 items-center gap-2 rounded-xl bg-[#14532d] px-5 text-sm font-bold text-white shadow-[0_10px_24px_rgba(20,83,45,.18)] transition hover:-translate-y-0.5 hover:bg-[#166534]">
                  {t("hero.primary")}<ArrowRight className="size-4" />
                </Link>
                <Link href={claimLink} className="inline-flex h-12 items-center gap-2 rounded-xl border border-[#d7e2da] bg-white px-5 text-sm font-bold text-[#30543b] transition hover:border-[#a8ceb2] hover:bg-[#f6fbf7]">
                  {t("hero.secondary")}<ArrowUpRight className="size-4" />
                </Link>
              </div>
              <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-medium text-[#708078]">
                <span className="inline-flex items-center gap-2"><ShieldCheck className="size-4 text-[#25814a]" />{t("hero.proof")}</span>
                <span className="h-1 w-1 rounded-full bg-[#a8b6ac]" />
                <span>{t("common.languages")}</span>
              </div>
              <div className="mt-8 inline-flex items-center gap-2 rounded-lg bg-[#eef5ef] px-3 py-2 text-[10px] font-bold uppercase tracking-[.12em] text-[#687c6c]"><Sparkles className="size-3.5 text-[#1d7843]" />{t("hero.demo")}</div>
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: .97, x: 14 }} animate={{ opacity: 1, scale: 1, x: 0 }} transition={{ duration: .7, delay: .1 }} className="relative mx-auto w-full max-w-[670px]">
              <div className="absolute -inset-5 rounded-[38px] bg-[#d7eadb]/60 blur-3xl" />
              <div className="relative overflow-hidden rounded-[30px] border border-white/80 bg-white p-2.5 shadow-[0_30px_90px_rgba(22,67,37,.17)]">
                <div className="relative h-[350px] overflow-hidden rounded-[23px] bg-[#b8cfaa] sm:h-[420px]">
                  <Image src="/images/goa-field-map.png" alt={t("landing.mapAlt")} fill priority className="hero-image" sizes="(max-width: 1024px) 100vw, 55vw" />
                  <div className="map-grid absolute inset-0 opacity-40" />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#0e2c1d]/55 via-transparent to-[#143d27]/10" />
                  <div className="absolute left-[35%] top-[25%] h-[38%] w-[30%] rotate-[-10deg] rounded-[34%_12%_27%_15%] border-2 border-dashed border-white/90 shadow-[0_0_0_999px_rgba(20,83,45,.06)]" />
                  <div className="absolute left-[52%] top-[44%] flex items-center gap-2 rounded-full border border-white/65 bg-[#14532d]/90 px-3 py-2 text-[10px] font-bold text-white shadow-lg backdrop-blur"><MapPinned className="size-3.5" /> {t("landing.plot")} {demoClaim?.surveyNumber ?? ""} <span className="size-1.5 rounded-full bg-[#8ef0ac]" /></div>
                  <div className="absolute left-4 top-4 rounded-xl border border-white/30 bg-[#173b28]/75 px-3 py-2 text-[9px] font-bold uppercase tracking-[.15em] text-white backdrop-blur-md sm:left-5 sm:top-5">{t("landing.monsoonLayer")}</div>
                  <div className="absolute bottom-4 left-4 flex items-center gap-2 rounded-lg border border-white/25 bg-white/90 px-3 py-2 text-[10px] font-semibold text-[#31523b] shadow sm:bottom-5 sm:left-5"><span className="size-2 rounded-full bg-[#54ba70]" /> {t("landing.syntheticLayer")}</div>
                </div>
                <div className="absolute left-5 top-[28%] hidden w-[200px] rounded-2xl border border-white/75 bg-white/95 p-3.5 shadow-[0_16px_45px_rgba(24,61,37,.19)] backdrop-blur sm:block float-soft">
                  <div className="flex items-center justify-between"><span className="text-[10px] font-bold uppercase tracking-[.12em] text-slate-400">{t("landing.claimStatus")}</span><span className="rounded-full bg-[#e6f6e9] px-2 py-1 text-[9px] font-extrabold text-[#176534]">{t("landing.inReview")}</span></div>
                  <div className="mt-3 text-sm font-extrabold text-slate-800">{demoClaim?.id ?? ""}</div>
                  <div className="mt-1 text-[11px] text-slate-500">{demoClaim?.farmerName ?? ""} · {schemeName}</div>
                  <div className="mt-3 flex items-center gap-1"><span className="h-1.5 flex-1 rounded-full bg-[#16a34a]" /><span className="h-1.5 flex-1 rounded-full bg-[#16a34a]" /><span className="h-1.5 flex-1 rounded-full bg-[#16a34a]" /><span className="h-1.5 flex-1 rounded-full bg-[#e7eee8]" /></div>
                  <div className="mt-2 text-[9px] font-medium text-slate-400">{t("landing.progress", { count: 5 })}</div>
                </div>
                <div className="absolute bottom-10 right-4 w-[190px] rounded-2xl border border-white/75 bg-white/95 p-3.5 shadow-[0_16px_45px_rgba(24,61,37,.19)] backdrop-blur sm:bottom-12 sm:right-5 sm:w-[215px]">
                  <div className="flex items-center gap-2"><span className="grid size-8 place-items-center rounded-lg bg-[#e6f6e9] text-[#176534]"><ShieldCheck className="size-4" /></span><span className="text-[10px] font-bold uppercase tracking-[.1em] text-slate-400">{t("landing.aiRecommendation")}</span></div>
                  <div className="mt-3 flex items-end justify-between"><span className="text-xl font-extrabold tracking-tight text-[#176534]">{laneName}</span><span className="rounded-full border border-[#bde4c7] px-2 py-1 text-[9px] font-bold text-[#176534]">{t("landing.officerReview")}</span></div>
                  <div className="mt-1 text-[10px] text-slate-500">{t("landing.evidenceAligned")}</div>
                  <div className="mt-3 border-t border-slate-100 pt-2 text-[9px] font-semibold text-[#667a6b]">{t("sections.ai")}</div>
                </div>
              </div>
              <div className="absolute -right-1 top-6 hidden size-14 items-center justify-center rounded-2xl border border-white bg-white text-[#166534] shadow-lg lg:flex"><MapPinned className="size-6" /></div>
            </motion.div>
          </div>
          <div className="app-container pb-6">
            <div className="flex flex-wrap items-center justify-between gap-4 border-t border-[#e2ebe4] pt-5 text-[11px] font-semibold text-[#728177]">
              <span>{t("landing.connectedJourney")}</span><span>{t("landing.documentVerification")}</span><span>{t("landing.registryComparison")}</span><span>{t("landing.floodEvidence")}</span><span>{t("landing.officerDecision")}</span>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="app-container scroll-mt-24 py-20 sm:py-24">
          <div className="mx-auto max-w-[650px] text-center"><div className="eyebrow">{t("landing.howEyebrow")}</div><h2 className="mt-4 text-3xl font-semibold tracking-[-.05em] text-[#173b28] sm:text-4xl">{t("sections.how")}</h2><p className="mt-4 text-sm leading-7 text-slate-500 sm:text-base">{t("sections.howBody")}</p></div>
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {flowKeys.map((key, index) => { const Icon = flowIcons[index]; return <motion.article key={key} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-80px" }} transition={{ delay: index * .08 }} className="surface group p-5 transition hover:-translate-y-1 hover:shadow-[0_18px_36px_rgba(20,83,45,.09)]"><div className="flex items-center justify-between"><span className="grid size-11 place-items-center rounded-xl bg-[#e9f5ec] text-[#176534]"><Icon className="size-5" /></span><span className="text-xs font-bold text-[#a4b2a7]">0{index + 1}</span></div><h3 className="mt-5 text-base font-bold text-slate-800">{t(key)}</h3><p className="mt-2 text-xs leading-6 text-slate-500">{t(flowDetailKeys[index])}</p></motion.article> })}
          </div>
        </section>

        <section id="schemes" className="scroll-mt-24 border-y border-[#e5ece7] bg-white py-20 sm:py-24">
          <div className="app-container grid gap-10 lg:grid-cols-[.72fr_1.28fr] lg:items-end">
            <div><div className="eyebrow">{t("landing.schemeEyebrow")}</div><h2 className="mt-4 max-w-md text-3xl font-semibold tracking-[-.05em] text-[#173b28] sm:text-4xl">{t("sections.schemes")}</h2><p className="mt-4 max-w-md text-sm leading-7 text-slate-500">{t("landing.schemeIntro")}</p><Link href="/rules" className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-[#176534]">{t("landing.exploreRules")}<ArrowRight className="size-4" /></Link></div>
            <div className="grid gap-4 md:grid-cols-2">
              <article className="rounded-[22px] border border-[#dcebe0] bg-[#f4faf5] p-6"><div className="flex items-center justify-between"><span className="grid size-11 place-items-center rounded-xl bg-white text-[#166534] shadow-sm"><Waves className="size-5" /></span><span className="rounded-full border border-[#cfe4d4] bg-white px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider text-[#51745b]">{t("landing.illustrative")}</span></div><h3 className="mt-6 text-xl font-bold tracking-tight text-[#173b28]">{t("claim.floodRelief")}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{t("landing.floodSchemeBody")}</p><div className="mt-5 flex items-center justify-between border-t border-[#deebe1] pt-4 text-xs"><span className="font-semibold text-slate-500">{t("landing.demoRate")}</span><span className="font-extrabold text-[#176534]">{formatINR(floodRule?.compensationRate ?? 9800)} / ha</span></div></article>
              <article className="rounded-[22px] border border-[#e2e8e4] bg-[#fbfcfb] p-6"><div className="flex items-center justify-between"><span className="grid size-11 place-items-center rounded-xl bg-white text-[#7a6732] shadow-sm"><WalletCards className="size-5" /></span><span className="rounded-full border border-[#e6e7df] bg-white px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider text-[#7b785f]">{t("landing.illustrative")}</span></div><h3 className="mt-6 text-xl font-bold tracking-tight text-[#173b28]">{t("claim.landAcquisition")}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{t("landing.acquisitionBody")}</p><div className="mt-5 flex items-center justify-between border-t border-[#e9ece8] pt-4 text-xs"><span className="font-semibold text-slate-500">{t("landing.humanReviewed")}</span><span className="font-extrabold text-[#526a56]">{t("landing.itemized")}</span></div></article>
            </div>
          </div>
        </section>

        <section className="app-container grid gap-12 py-20 sm:py-24 lg:grid-cols-2 lg:items-center">
          <div><div className="eyebrow">{t("landing.accountabilityEyebrow")}</div><h2 className="mt-4 text-3xl font-semibold tracking-[-.05em] text-[#173b28] sm:text-4xl">{t("sections.why")}</h2><p className="mt-4 max-w-xl text-sm leading-7 text-slate-500">{t("landing.accountabilityBody")}</p><div className="mt-8 grid gap-4 sm:grid-cols-2"><div className="rounded-2xl border border-[#e2ebe4] bg-white p-4"><div className="mb-3 grid size-9 place-items-center rounded-lg bg-[#e8f5eb] text-[#166534]"><Languages className="size-4" /></div><h3 className="text-sm font-bold text-slate-800">{t("sections.access")}</h3><p className="mt-1 text-xs leading-5 text-slate-500">{t("landing.languages")}</p></div><div className="rounded-2xl border border-[#e2ebe4] bg-white p-4"><div className="mb-3 grid size-9 place-items-center rounded-lg bg-[#e8f5eb] text-[#166534]"><UsersRound className="size-4" /></div><h3 className="text-sm font-bold text-slate-800">{t("sections.csc")}</h3><p className="mt-1 text-xs leading-5 text-slate-500">{t("landing.cscBody")}</p></div></div></div>
          <div className="relative rounded-[26px] border border-[#dfe9e2] bg-white p-6 shadow-[0_24px_60px_rgba(20,83,45,.07)] sm:p-8"><div className="absolute right-6 top-6 grid size-11 place-items-center rounded-xl bg-[#e7f5eb] text-[#176534]"><ShieldCheck className="size-5" /></div><div className="eyebrow">{t("landing.principle")}</div><h3 className="mt-6 max-w-sm text-3xl font-semibold tracking-[-.05em] text-[#173b28]">{t("sections.ai")}</h3><p className="mt-4 max-w-lg text-sm leading-7 text-slate-500">{t("sections.aiBody")}</p><div className="mt-7 rounded-2xl border border-[#dcebe0] bg-[#f4faf5] p-4"><div className="flex items-start gap-3"><div className="grid size-8 shrink-0 place-items-center rounded-full bg-[#dff2e4] text-[#176534]"><Check className="size-4" /></div><div><div className="text-sm font-bold text-[#245636]">{t("landing.recommendationDecision")}</div><p className="mt-1 text-xs leading-5 text-[#5f7465]">{t("landing.lanesBody")}</p></div></div></div><div className="mt-5 grid grid-cols-3 gap-2">{[[t("status.laneGreen"), "#176534", "#e6f6e9"], [t("status.laneAmber"), "#946100", "#fff5df"], [t("status.laneRed"), "#b42318", "#fff0ef"]].map(([label, color, bg]) => <div key={label} style={{ color, background: bg }} className="rounded-lg py-2 text-center text-[10px] font-extrabold tracking-widest">{label}</div>)}</div></div>
        </section>

        <section className="border-y border-[#e4ece6] bg-[#f0f7f2] py-16 sm:py-20">
          <div className="app-container grid gap-6 md:grid-cols-3">
            <article className="rounded-2xl border border-white bg-white p-6"><div className="grid size-10 place-items-center rounded-xl bg-[#e6f4e9] text-[#176534]"><MapPinned className="size-5" /></div><h3 className="mt-5 text-base font-bold text-[#173b28]">{t("sections.flood")}</h3><p className="mt-2 text-sm leading-6 text-slate-500">{t("sections.floodBody")}</p><div className="mt-5 rounded-xl bg-[#f5f8f5] p-3 text-xs leading-5 text-[#526858]">{t("landing.floodNotice", { date: evidenceDate })}</div><div className="mt-3 text-[10px] font-semibold uppercase tracking-wider text-slate-400">{t("landing.syntheticEvidence")}</div></article>
            <article className="rounded-2xl border border-white bg-white p-6"><div className="grid size-10 place-items-center rounded-xl bg-[#e6f4e9] text-[#176534]"><WalletCards className="size-5" /></div><h3 className="mt-5 text-base font-bold text-[#173b28]">{t("sections.calculate")}</h3><p className="mt-2 text-sm leading-6 text-slate-500">{t("landing.calculationBody")}</p><div className="mt-5 flex items-center justify-between rounded-xl bg-[#f5f8f5] p-3"><span className="text-xs text-slate-500">{hectares.toLocaleString("en-IN", { maximumFractionDigits: 2 })} ha × {formatINR(floodRule?.compensationRate ?? 9800)}</span><strong className="text-sm text-[#176534]">{formatINR(demoClaim?.compensation ?? 24500)}</strong></div></article>
            <article className="rounded-2xl border border-white bg-white p-6"><div className="grid size-10 place-items-center rounded-xl bg-[#e6f4e9] text-[#176534]"><CircleHelp className="size-5" /></div><h3 className="mt-5 text-base font-bold text-[#173b28]">{t("sections.support")}</h3><p className="mt-2 text-sm leading-6 text-slate-500">{t("landing.helpBody")}</p><Link href="/csc" className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-[#176534]">{t("cta.csc")}<ArrowRight className="size-4" /></Link></article>
          </div>
        </section>

        <section id="help" className="app-container py-20 sm:py-24">
          <div className="relative overflow-hidden rounded-[28px] bg-[#14532d] px-6 py-10 text-white sm:px-12 sm:py-14"><div className="absolute -right-20 -top-24 size-80 rounded-full border border-white/10" /><div className="absolute -right-7 -top-12 size-56 rounded-full border border-white/10" /><div className="relative flex flex-col items-start justify-between gap-8 md:flex-row md:items-center"><div><div className="text-[10px] font-bold uppercase tracking-[.18em] text-[#a5d8b3]">{t("landing.demoLabel")}</div><h2 className="mt-4 max-w-xl text-3xl font-semibold tracking-[-.05em] sm:text-4xl">{t("landing.footerTitle")}</h2><p className="mt-3 max-w-lg text-sm leading-6 text-white/70">{t("landing.footerBody")}</p></div><div className="flex flex-wrap gap-3"><Link href="/verify" className="inline-flex h-11 items-center gap-2 rounded-xl bg-white px-4 text-sm font-bold text-[#14532d] transition hover:bg-[#eaf6ed]">{t("cta.start")}<ArrowUpRight className="size-4" /></Link><Link href="/csc" className="inline-flex h-11 items-center gap-2 rounded-xl border border-white/25 px-4 text-sm font-bold text-white transition hover:bg-white/10">{t("cta.csc")}<ArrowDownRight className="size-4" /></Link></div></div></div>
        </section>
      </main>
      <footer className="border-t border-[#e4ece6] bg-white">
        <div className="app-container flex flex-col gap-6 py-7 sm:flex-row sm:items-center sm:justify-between"><div><div className="text-sm font-extrabold text-[#173b28]">CivicNode Goa</div><div className="mt-1 text-xs text-slate-500">{t("brand.tagline")}</div></div><div className="flex flex-wrap gap-x-5 gap-y-2 text-xs font-semibold text-slate-500"><Link href="/cases" className="hover:text-[#14532d]">{t("landing.officerWorkspace")}</Link><Link href="/dashboard" className="hover:text-[#14532d]">{t("cta.dashboard")}</Link><Link href="/rules" className="hover:text-[#14532d]">{t("landing.demoRules")}</Link><a href="#help" className="hover:text-[#14532d]">{t("landing.footerHelp")}</a></div></div>
      </footer>
    </div>
  )
}
