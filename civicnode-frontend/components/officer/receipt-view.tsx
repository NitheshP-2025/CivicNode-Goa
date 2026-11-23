"use client"

import { useState } from "react"
import Link from "next/link"
import { jsPDF } from "jspdf"
import { ArrowLeft, BadgeCheck, CheckCircle2, Download, FileCheck2, Printer, ShieldAlert, ShieldCheck } from "lucide-react"
import { OfficerShell } from "@/components/shared/officer-shell"
import { LaneBadge } from "@/components/shared/status-badges"
import { useCivic } from "@/hooks/use-civic"
import { apiRequest, DEMO_MODE } from "@/lib/api-client"
import { calculateCompensation } from "@/lib/compensation"
import { formatINR } from "@/lib/format"

export function ReceiptView({ id }: { id: string }) {
  const { claims, rules, isReady, notify } = useCivic()
  const claim = claims.find((item) => item.id === id)
  const [auditState, setAuditState] = useState<"idle" | "verified" | "unavailable" | "error">("idle")
  const [checking, setChecking] = useState(false)
  const calculation = claim ? calculateCompensation(claim, rules.find((rule) => rule.scheme === claim.scheme)) : null

  async function verifyAudit() {
    if (DEMO_MODE) {
      setAuditState("unavailable")
      notify("Cryptographic audit verification is unavailable for synthetic demo records.")
      return
    }
    setChecking(true)
    try {
      const result = await apiRequest<{ valid: boolean; reference: string; verifiedAt: string }>(`/api/claims/${encodeURIComponent(id)}/audit/verify`, { method: "POST" })
      setAuditState(result.valid ? "verified" : "error")
    } catch {
      setAuditState("error")
    } finally { setChecking(false) }
  }

  function downloadPdf() {
    if (!claim || !claim.decision || !calculation) return
    const pdf = new jsPDF({ unit: "pt", format: "a4" })
    const left = 48
    let y = 56
    pdf.setFillColor(20, 83, 45)
    pdf.roundedRect(left, y - 20, 36, 36, 8, 8, "F")
    pdf.setTextColor(255, 255, 255)
    pdf.setFontSize(17)
    pdf.text("C", left + 11, y + 4)
    pdf.setTextColor(30, 41, 59)
    pdf.setFont("helvetica", "bold")
    pdf.setFontSize(19)
    pdf.text("CivicNode Goa", left + 48, y - 2)
    pdf.setFont("helvetica", "normal")
    pdf.setFontSize(9)
    pdf.setTextColor(100, 116, 139)
    pdf.text("Digital claim receipt · Demonstration record", left + 48, y + 14)
    y += 48
    pdf.setDrawColor(220, 233, 223)
    pdf.line(left, y, 548, y)
    y += 26
    pdf.setFont("helvetica", "bold")
    pdf.setFontSize(14)
    pdf.setTextColor(20, 83, 45)
    pdf.text(`Receipt RCP-${claim.id}`, left, y)
    y += 28
    const rows = [
      ["Claim ID", claim.id], ["Farmer", claim.farmerName], ["Scheme", claim.scheme], ["Survey number", `${claim.surveyNumber}/${claim.subdivision}`],
      ["Taluka / village", `${claim.taluka} / ${claim.village}`], ["Documents considered", claim.documents.join(", ") || "Synthetic demonstration documents"],
      ["Rule version", claim.ruleVersion], ["Officer decision", claim.decision.action.replaceAll("-", " ").toUpperCase()], ["Officer", claim.decision.officer],
      ["Decision date", new Date(claim.decision.decidedAt).toLocaleString("en-IN")], ["Compensation estimate", formatINR(calculation.total)],
      ["Calculation", calculation.formula], ["Audit reference", `AUD-${claim.id}-DEMO`],
    ]
    for (const [label, value] of rows) {
      if (y > 760) { pdf.addPage(); y = 56 }
      pdf.setFont("helvetica", "bold")
      pdf.setFontSize(9)
      pdf.setTextColor(100, 116, 139)
      pdf.text(label, left, y)
      pdf.setFont("helvetica", "normal")
      pdf.setTextColor(30, 41, 59)
      const wrapped = pdf.splitTextToSize(value, 325)
      pdf.text(wrapped, 205, y)
      y += Math.max(20, wrapped.length * 12 + 6)
    }
    y += 8
    pdf.setFillColor(245, 250, 246)
    pdf.roundedRect(left, y, 500, 46, 8, 8, "F")
    pdf.setFontSize(8)
    pdf.setTextColor(81, 104, 87)
    pdf.text("AI recommendations support review only. The officer decision is shown separately. This synthetic receipt is not a legal certificate or payment instruction.", left + 12, y + 19, { maxWidth: 476 })
    pdf.save(`CivicNode-${claim.id}-receipt.pdf`)
  }

  return <OfficerShell active="Audit & receipts"><div className="mx-auto max-w-[940px]">
    <div className="no-print mb-5 flex flex-wrap items-end justify-between gap-4"><div><Link href={`/cases/${id}`} className="mb-4 inline-flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-[#14532d]"><ArrowLeft className="size-4" />Back to case review</Link><div className="eyebrow">Decision record · auditable by design</div><h1 className="mt-2 text-3xl font-semibold tracking-[-.05em] text-slate-800">Digital receipt</h1></div>{claim?.decision && <div className="flex gap-2"><button type="button" onClick={() => window.print()} className="inline-flex h-10 items-center gap-2 rounded-lg border border-[#dce7de] bg-white px-3 text-xs font-bold text-slate-600 hover:border-[#a6c6ad]"><Printer className="size-4" />Print</button><button type="button" onClick={downloadPdf} className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#14532d] px-3 text-xs font-bold text-white hover:bg-[#166534]"><Download className="size-4" />Download PDF</button></div>}</div>
    {!isReady ? <div className="rounded-2xl border border-[#e2eae4] bg-white p-8 text-sm text-slate-500">Loading decision record…</div> : !claim ? <div className="rounded-2xl border border-[#e2eae4] bg-white p-8 text-sm text-slate-500">No claim was found for this receipt.</div> : !claim.decision ? <section className="rounded-2xl border border-[#e2eae4] bg-white p-8 text-center"><span className="mx-auto grid size-12 place-items-center rounded-2xl bg-[#fff5df] text-[#986700]"><ShieldAlert className="size-6" /></span><h2 className="mt-4 text-lg font-bold text-slate-800">No officer decision recorded yet</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">A receipt is generated only after an officer records a final decision. AI recommendations never create a receipt or authorize payment.</p><Link href={`/cases/${id}`} className="mt-5 inline-flex h-10 items-center gap-2 rounded-lg bg-[#14532d] px-4 text-xs font-bold text-white">Open case review</Link></section> : <>
      <article className="receipt-paper overflow-hidden rounded-3xl border border-[#dce7de] bg-white shadow-[0_16px_50px_rgba(20,60,35,.08)]"><div className="h-2 bg-[#14532d]" /><header className="flex flex-wrap items-start justify-between gap-4 border-b border-[#e8eee9] p-6 sm:p-9"><div className="flex items-center gap-3"><span className="grid size-12 place-items-center rounded-2xl bg-[#14532d] text-white"><span className="text-xl font-black">C</span></span><div><div className="text-lg font-extrabold tracking-tight text-slate-800">CivicNode Goa</div><div className="text-[10px] font-bold uppercase tracking-[.13em] text-[#708276]">Transparent relief · accountable decisions</div></div></div><div className="text-right"><div className="text-[9px] font-bold uppercase tracking-[.13em] text-slate-400">Receipt number</div><div className="mt-1 font-mono text-xs font-bold text-slate-700">RCP-{claim.id}</div><div className="mt-1 text-[10px] text-slate-400">Issued {new Date(claim.decision.decidedAt).toLocaleDateString("en-IN")}</div></div></header>
        <div className="grid gap-0 lg:grid-cols-[1fr_280px]"><div className="p-6 sm:p-9"><div className="text-[9px] font-bold uppercase tracking-[.14em] text-[#7b8d7e]">Claim decision receipt</div><h2 className="mt-2 text-2xl font-semibold tracking-[-.04em] text-slate-800">{claim.farmerName}</h2><p className="mt-1 text-xs text-slate-500">Claim {claim.id} · {claim.scheme}</p><div className="mt-6 grid gap-3 sm:grid-cols-2">{[["Survey number", `${claim.surveyNumber}/${claim.subdivision}`], ["Taluka / village", `${claim.taluka} / ${claim.village}`], ["Submitted", new Date(claim.submittedAt).toLocaleDateString("en-IN")], ["Assigned officer", claim.assignedOfficer]].map(([label, value]) => <div key={label} className="rounded-xl border border-[#edf1ee] bg-[#fbfcfb] p-3"><div className="text-[9px] font-bold uppercase tracking-[.1em] text-slate-400">{label}</div><div className="mt-1 text-xs font-bold text-slate-700">{value}</div></div>)}</div>
          <section className="mt-7"><h3 className="text-xs font-extrabold text-slate-700">Documents considered</h3><div className="mt-2 flex flex-wrap gap-2">{claim.documents.map((name) => <span key={name} className="inline-flex items-center gap-1.5 rounded-lg border border-[#e2eae4] bg-white px-2.5 py-1.5 text-[10px] font-semibold text-slate-600"><FileCheck2 className="size-3.5 text-[#37814d]" />{name}</span>)}</div></section>
          <section className="mt-7 rounded-2xl border border-[#e2eae4] p-4"><div className="flex items-center justify-between gap-3"><h3 className="text-xs font-extrabold text-slate-700">Deterministic compensation breakdown</h3><span className="text-sm font-extrabold text-[#14532d]">{formatINR(calculation?.total ?? 0)}</span></div><p className="mt-1 text-[10px] text-slate-400">Formula: {calculation?.formula}</p><div className="mt-3 flex flex-col gap-2">{calculation?.rows.map((row) => <div key={row.label} className="flex items-start justify-between gap-4 border-t border-[#edf1ee] pt-2 text-[10px]"><span className="text-slate-500">{row.label}{row.note && <span className="mt-0.5 block text-[9px] text-slate-400">{row.note}</span>}</span><span className="shrink-0 font-bold text-slate-700">{row.label === "Eligible land area" ? `${row.amount.toFixed(3)} ha` : formatINR(row.amount)}</span></div>)}</div></section>
          <div className="mt-7 rounded-xl border border-[#f0e2bb] bg-[#fff9eb] p-3 text-[10px] leading-5 text-[#81621a]"><b>Illustrative rule reference.</b> {claim.ruleVersion} · Demo condition 1. This is not a legal citation or statement of actual government policy.</div></div>
          <aside className="border-t border-[#e8eee9] bg-[#f8faf8] p-6 sm:p-8 lg:border-l lg:border-t-0"><div className="text-[9px] font-bold uppercase tracking-[.13em] text-slate-400">AI recommendation</div><div className="mt-2"><LaneBadge lane={claim.recommendation} /></div><p className="mt-2 text-[10px] leading-5 text-slate-500">AI-generated recommendation. Human decision required. The recommendation is separate from the officer&apos;s decision.</p><div className="mt-5 border-t border-[#e3eae4] pt-5"><div className="text-[9px] font-bold uppercase tracking-[.13em] text-slate-400">Officer decision</div><div className="mt-2 rounded-xl border border-[#cfe3d3] bg-white p-3"><div className="flex items-center gap-2 text-xs font-extrabold capitalize text-[#14532d]"><BadgeCheck className="size-4" />{claim.decision.action.replaceAll("-", " ")}</div><p className="mt-2 text-[10px] leading-5 text-slate-600">{claim.decision.remarks}</p><div className="mt-3 border-t border-[#edf1ee] pt-2 text-[9px] text-slate-400">Recorded by {claim.decision.officer}<br />{new Date(claim.decision.decidedAt).toLocaleString("en-IN")}</div></div></div><div className="mt-5 border-t border-[#e3eae4] pt-5"><div className="text-[9px] font-bold uppercase tracking-[.13em] text-slate-400">Audit reference</div><div className="mt-2 rounded-lg bg-white p-2.5 font-mono text-[10px] font-bold text-slate-600">AUD-{claim.id}-DEMO</div><p className="mt-2 text-[9px] leading-4 text-slate-400">Synthetic reference only. No cryptographic proof is represented.</p><button type="button" disabled={checking} onClick={verifyAudit} className="mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-[#cfddd2] bg-white px-3 text-[10px] font-bold text-[#31543c] disabled:opacity-50"><ShieldCheck className="size-3.5" />{checking ? "Checking…" : "Verify audit record"}</button>{auditState === "verified" && <div role="status" className="mt-2 flex items-center gap-1.5 text-[10px] font-bold text-green-700"><CheckCircle2 className="size-3.5" />Backend verified this record</div>}{auditState === "unavailable" && <div role="status" className="mt-2 text-[10px] leading-4 text-amber-700">Demo record: cryptographic verification is unavailable.</div>}{auditState === "error" && <div role="alert" className="mt-2 text-[10px] leading-4 text-red-700">The backend did not confirm this audit record.</div>}</div></aside></div>
        <footer className="border-t border-[#e8eee9] px-6 py-4 text-[9px] leading-4 text-slate-400 sm:px-9">CivicNode Goa demonstration interface. Not a government-issued certificate, payment instruction, or confirmation of actual damage. Final decisions are made by authorized officers.</footer></article>
      <div className="no-print mt-4 flex items-start gap-2 rounded-xl border border-[#dce9df] bg-[#f2f8f3] p-3 text-[10px] leading-5 text-[#596e5e]"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-[#34824c]" />AI recommendations and officer decisions are recorded separately. Satellite indicators describe water coverage only; crop damage must be confirmed by an officer.</div>
    </>}
  </div></OfficerShell>
}
