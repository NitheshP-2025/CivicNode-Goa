"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { ArrowLeft, ArrowUpRight, Check, Circle, Clock3, FileCheck2, MapPin, ShieldCheck } from "lucide-react"
import { useMemo } from "react"
import { SiteHeader } from "@/components/shared/site-header"
import { LaneBadge, StatusBadge } from "@/components/shared/status-badges"
import { useCivic } from "@/hooks/use-civic"
import { useT } from "@/hooks/use-translations"
import type { CivicClaim } from "@/types/civic"

const stages = [
  { label: "status.stage1", detail: "status.detail1" },
  { label: "status.stage2", detail: "status.detail2" },
  { label: "status.stage3", detail: "status.detail3" },
  { label: "status.stage4", detail: "status.detail4" },
  { label: "status.stage5", detail: "status.detail5" },
  { label: "status.stage6", detail: "status.detail6" },
  { label: "status.stage7", detail: "status.detail7" },
  { label: "status.stage8", detail: "status.detail8" },
  { label: "status.stage9", detail: "status.detail9" },
] as const

function stageIndex(claim: CivicClaim) {
  if (claim.status === "Submitted") return 1
  if (claim.status === "Under Verification" || claim.status === "Awaiting Information") return 1
  if (claim.status === "Field Inspection Required") return 3
  if (claim.status === "Under Officer Review") return 6
  if (claim.status === "Approved" || claim.status === "Rejected") return 7
  if (claim.status === "Payment Processing") return 8
  return 9
}

function localizeStatus(status: CivicClaim["status"], t: ReturnType<typeof useT>) {
  const key: Record<CivicClaim["status"], Parameters<typeof t>[0]> = {
    Submitted: "status.statusSubmitted",
    "Under Verification": "status.statusVerification",
    "Awaiting Information": "status.statusInformation",
    "Field Inspection Required": "status.statusInspection",
    "Under Officer Review": "status.statusReview",
    Approved: "status.statusApproved",
    Rejected: "status.statusRejected",
    "Payment Processing": "status.statusPayment",
    Paid: "status.statusPaid",
  }
  return t(key[status])
}

export function ClaimStatusView({ id }: { id: string }) {
  const t = useT()
  const { claims, isReady } = useCivic()
  const claim = useMemo(() => claims.find((item) => item.id === id), [claims, id])
  const active = claim ? stageIndex(claim) : 0

  if (!isReady) return <div className="min-h-screen bg-[#f7faf8]"><SiteHeader /><main className="app-container py-16"><div className="surface mx-auto max-w-3xl p-8 text-sm text-slate-500">{t("common.loading")}…</div></main></div>
  if (!claim) return <div className="min-h-screen bg-[#f7faf8]"><SiteHeader /><main className="app-container py-16"><div className="surface mx-auto max-w-2xl p-8 text-center"><div className="eyebrow">{t("common.demo")}</div><h1 className="mt-3 text-2xl font-bold text-[#173b28]">{t("status.notFound")}</h1><p className="mt-2 text-sm text-slate-500">{t("status.notFoundBody")}</p><Link href="/" className="mt-5 inline-flex h-10 items-center gap-2 rounded-xl bg-[#14532d] px-4 text-xs font-bold text-white">{t("nav.home")}<ArrowUpRight className="size-4" /></Link></div></main></div>

  const lastUpdate = claim.activity.at(-1)
  const isTerminal = claim.status === "Approved" || claim.status === "Rejected" || claim.status === "Paid"
  return <div className="min-h-screen bg-[#f7faf8]"><SiteHeader /><main className="app-container max-w-[1100px] py-7 sm:py-10">
    <Link href="/" className="mb-5 inline-flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-[#14532d]"><ArrowLeft className="size-4" />{t("nav.home")}</Link>
    <section className="surface overflow-hidden">
      <div className="relative overflow-hidden bg-[#153d2b] px-5 py-7 text-white sm:px-8 sm:py-9"><div className="absolute -right-12 -top-24 size-64 rounded-full border border-white/10" /><div className="absolute -right-2 -top-12 size-44 rounded-full border border-white/10" /><div className="relative flex flex-wrap items-start justify-between gap-5"><div><div className="text-[10px] font-bold uppercase tracking-[.17em] text-white/55">{t("status.claimReference")}</div><h1 className="mt-2 text-3xl font-semibold tracking-[-.05em] sm:text-4xl">{claim.id}</h1><p className="mt-2 text-sm text-white/70">{claim.farmerName} · {claim.taluka}, {claim.district}</p></div><div className="flex flex-col items-start gap-2 sm:items-end"><StatusBadge status={claim.status} /><span className="text-xs text-white/55">{t("status.human")}</span></div></div><div className="relative mt-7 grid gap-3 border-t border-white/10 pt-5 text-xs sm:grid-cols-4"><Summary label={t("status.scheme")} value={claim.scheme === "Flood Relief" ? t("claim.floodRelief") : t("claim.landAcquisition")} /><Summary label={t("claim.survey")} value={`${claim.surveyNumber}/${claim.subdivision}`} /><Summary label={t("status.submitted")} value={new Date(claim.submittedAt).toLocaleDateString()} /><Summary label={t("status.current")} value={localizeStatus(claim.status, t)} /></div></div>
      <div className="grid gap-6 p-5 sm:p-8 lg:grid-cols-[1fr_310px]">
        <section><div className="mb-5 flex items-end justify-between gap-4"><div><div className="eyebrow">{t("status.timelineEyebrow")}</div><h2 className="mt-2 text-xl font-bold tracking-tight text-slate-800">{t("status.title")}</h2></div><div className="hidden text-right text-[10px] text-slate-400 sm:block">{t("common.demo")}</div></div>
          <ol className="relative flex flex-col">{stages.map((stage, index) => {
            const complete = index < active || (isTerminal && index <= 7) || (claim.status === "Paid" && index === 8)
            const current = index === active && !complete
            const activity = claim.activity.find((item) => item.label.toLowerCase().includes(["submitted", "document", "registry", "flood", "rules", "compensation", "officer", "decision", "payment"][index]))
            return <motion.li key={stage.label} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * .035 }} className="relative grid grid-cols-[34px_1fr] gap-3 pb-6 last:pb-0"><span aria-hidden="true" className={`relative z-10 grid size-8 place-items-center rounded-full border ${complete ? "border-[#198546] bg-[#198546] text-white" : current ? "border-[#16a34a] bg-[#edf8ef] text-[#14532d] ring-4 ring-[#eff8f1]" : "border-[#dfe7e1] bg-white text-slate-300"}`}>{complete ? <Check className="size-4" /> : current ? <Clock3 className="size-4" /> : <Circle className="size-3" />}</span>{index < stages.length - 1 && <span aria-hidden="true" className={`absolute left-[15px] top-8 h-[calc(100%-22px)] w-px ${complete ? "bg-[#91c79e]" : "bg-[#e4ebe6]"}`} />}<div className="min-w-0 pt-0.5"><div className="flex flex-wrap items-center gap-2"><h3 className={`text-sm font-bold ${current ? "text-[#14532d]" : complete ? "text-slate-800" : "text-slate-400"}`}>{t(stage.label)}</h3>{current && <span className="rounded-full bg-[#e8f5eb] px-2 py-0.5 text-[9px] font-extrabold uppercase tracking-wide text-[#176534]">{t("status.current")}</span>}</div><p className={`mt-1 text-xs leading-5 ${current || complete ? "text-slate-500" : "text-slate-400"}`}>{t(stage.detail)}</p>{complete && activity && <p className="mt-1 text-[10px] text-slate-400">{new Date(activity.at).toLocaleString()}</p>}{current && <p className="mt-2 rounded-lg border border-[#e5eee7] bg-[#f7faf8] p-2.5 text-[11px] leading-5 text-slate-600">{currentDetail(claim, t)}</p>}</div></motion.li>
          })}</ol>
        </section>
        <aside className="flex flex-col gap-4">
          <div className="rounded-2xl border border-[#e1eae3] bg-[#fbfdfb] p-4"><div className="flex items-center gap-2 text-xs font-extrabold text-slate-700"><ShieldCheck className="size-4 text-[#176534]" />{t("status.recommendation")}</div><div className="mt-3"><LaneBadge lane={claim.recommendation} label={t(`status.lane${claim.recommendation.charAt(0).toUpperCase()}${claim.recommendation.slice(1)}` as Parameters<typeof t>[0])} /></div><p className="mt-3 text-xs leading-5 text-slate-500">{claim.recommendationReasons[0]}</p><p className="mt-3 border-t border-[#e6eee8] pt-3 text-[10px] leading-4 text-slate-400">{t("status.human")}</p></div>
          <div className="rounded-2xl border border-[#e1eae3] bg-white p-4"><div className="flex items-center gap-2 text-xs font-extrabold text-slate-700"><FileCheck2 className="size-4 text-[#176534]" />{t("status.latestUpdate")}</div><p className="mt-3 text-xs font-semibold text-slate-700">{lastUpdate ? localizedActivity(lastUpdate.label, t) : t("status.awaitingUpdate")}</p><p className="mt-1 text-[11px] leading-5 text-slate-500">{lastUpdate?.detail || t("status.awaitingUpdate")}</p><p className="mt-2 text-[10px] text-slate-400">{lastUpdate ? new Date(lastUpdate.at).toLocaleString() : "—"}</p></div>
          <div className="rounded-2xl border border-[#e1eae3] bg-white p-4"><div className="flex items-center gap-2 text-xs font-extrabold text-slate-700"><MapPin className="size-4 text-[#176534]" />{t("status.landLocation")}</div><p className="mt-3 text-xs text-slate-600">{claim.village}, {claim.taluka}</p><p className="mt-1 text-[10px] text-slate-400">{claim.surveyNumber}/{claim.subdivision} · {claim.landArea} {t(claim.areaUnit === "hectares" ? "claim.hectares" : "claim.acres")}</p></div>
        </aside>
      </div>
      {claim.decision && <div className="mx-5 mb-6 rounded-xl border border-[#dfe9e2] bg-[#f8fbf9] p-4 sm:mx-8"><div className="text-xs font-bold text-slate-700">{t("status.officerDecision")}</div><p className="mt-1 text-xs leading-5 text-slate-600">{claim.decision.remarks || localizeStatus(claim.status, t)}</p><p className="mt-2 text-[10px] text-slate-400">{claim.decision.officer} · {new Date(claim.decision.decidedAt).toLocaleString()}</p></div>}
    </section>
  </main></div>
}

function Summary({ label, value }: { label: string; value: string }) {
  return <div><div className="text-[10px] font-semibold text-white/45">{label}</div><div className="mt-1 font-bold text-white">{value}</div></div>
}

function currentDetail(claim: CivicClaim, t: ReturnType<typeof useT>) {
  if (claim.status === "Awaiting Information") return t("status.detailInfoNeeded")
  if (claim.status === "Field Inspection Required") return t("status.detailInspection")
  if (claim.status === "Under Officer Review") return t("status.detailOfficer")
  if (claim.status === "Approved") return t("status.detailApproved")
  if (claim.status === "Rejected") return t("status.detailRejected")
  if (claim.status === "Payment Processing") return t("status.detailPayment")
  if (claim.status === "Paid") return t("status.detailPaid")
  return t("status.detailSubmitted")
}

function localizedActivity(label: string, t: ReturnType<typeof useT>) {
  if (label.toLowerCase().includes("submitted")) return t("status.stage1")
  if (label.toLowerCase().includes("document")) return t("status.stage2")
  if (label.toLowerCase().includes("registry")) return t("status.stage3")
  if (label.toLowerCase().includes("flood")) return t("status.stage4")
  if (label.toLowerCase().includes("compensation")) return t("status.stage6")
  if (label.toLowerCase().includes("approved")) return t("status.statusApproved")
  if (label.toLowerCase().includes("rejected")) return t("status.statusRejected")
  if (label.toLowerCase().includes("information")) return t("status.statusInformation")
  if (label.toLowerCase().includes("inspection")) return t("status.statusInspection")
  return label
}
