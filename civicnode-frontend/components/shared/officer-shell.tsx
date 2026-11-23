"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Activity, BarChart3, ClipboardCheck, FileClock, Leaf, LogOut, Menu, ShieldCheck, SlidersHorizontal } from "lucide-react"
import { useState } from "react"
import { LanguageSelect, RoleLinks } from "@/components/shared/site-header"

const navItems = [
  { label: "Overview", href: "/cases", icon: Activity },
  { label: "Case queue", href: "/cases", icon: ClipboardCheck },
  { label: "Analytics", href: "/dashboard", icon: BarChart3 },
  { label: "Rules management", href: "/rules", icon: SlidersHorizontal },
  { label: "Audit & receipts", href: "/receipt/CG-2026-001", icon: FileClock },
]

export function OfficerShell({ children, active = "" }: { children: React.ReactNode; active?: string }) {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const sidebar = (
    <>
      <div className="mb-9 flex items-center gap-3 px-3 pt-3">
        <span className="grid size-10 place-items-center rounded-xl bg-[#14532d] text-white"><Leaf className="size-5" /></span>
        <span><span className="block text-sm font-extrabold tracking-tight text-slate-800">CivicNode</span><span className="text-[10px] font-bold uppercase tracking-[.15em] text-slate-400">Goa · Officer</span></span>
      </div>
      <div className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[.15em] text-slate-400">Workspace</div>
      <nav className="flex flex-col gap-1" aria-label="Officer navigation">
        {navItems.map(({ label, href, icon: Icon }) => {
          const selected = active === label || (label === "Case queue" && pathname.startsWith("/cases")) || (label === "Analytics" && pathname.startsWith("/dashboard")) || (label === "Rules management" && pathname.startsWith("/rules")) || (label === "Audit & receipts" && pathname.startsWith("/receipt"))
          return <Link key={label} href={href} data-active={selected} className="sidebar-link"><Icon className="size-[17px]" aria-hidden="true" /><span>{label}</span></Link>
        })}
      </nav>
      <div className="mt-auto rounded-2xl border border-[#dcebe0] bg-white p-4">
        <div className="mb-2 flex items-center gap-2 text-xs font-bold text-[#14532d]"><ShieldCheck className="size-4" />Human decision required</div>
        <p className="text-[11px] leading-5 text-slate-500">AI recommendations support review. They never approve or reject a claim.</p>
      </div>
      <Link href="/" className="mt-5 flex items-center gap-2 px-3 pb-3 text-xs font-semibold text-slate-500 hover:text-[#14532d]"><LogOut className="size-4" />Switch to farmer portal</Link>
    </>
  )
  return (
    <div className="min-h-screen bg-[#f7faf8]">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col border-r border-[#e3ebe5] bg-[#f1f7f3] px-4 py-5 xl:flex">{sidebar}</aside>
      {mobileOpen && <div className="fixed inset-0 z-50 bg-slate-950/30 xl:hidden" onClick={() => setMobileOpen(false)}>
        <aside className="flex h-full w-[280px] flex-col bg-[#f1f7f3] px-4 py-5" onClick={(event) => event.stopPropagation()}>{sidebar}</aside>
      </div>}
      <div className="xl:pl-[248px]">
        <header className="no-print sticky top-0 z-20 flex h-[68px] items-center justify-between border-b border-[#e6ede8] bg-white/90 px-4 backdrop-blur-xl sm:px-7">
          <div className="flex items-center gap-3">
            <button type="button" aria-label="Open officer navigation" onClick={() => setMobileOpen(true)} className="grid size-9 place-items-center rounded-lg border border-[#e5ece7] text-[#14532d] xl:hidden"><Menu className="size-4" /></button>
            <div className="hidden items-center gap-2 text-xs text-slate-400 sm:flex"><span>Revenue & Disaster Management</span><span>/</span><span className="font-semibold text-slate-700">{active || "Workspace"}</span></div>
            <span className="rounded-full bg-[#fff7e6] px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-[#9a6700] sm:hidden">Demo workspace</span>
          </div>
          <div className="flex items-center gap-3"><RoleLinks active="officer" /><LanguageSelect compact /><div className="hidden size-9 items-center justify-center rounded-full bg-[#e6f1e8] text-xs font-extrabold text-[#14532d] sm:flex">PN</div></div>
        </header>
        <main className="px-4 py-7 sm:px-7 lg:px-9">{children}</main>
        <div className="pointer-events-none fixed bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-full border border-[#dce9df] bg-white/90 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.12em] text-[#5d7463] shadow-sm xl:left-[calc(50%+124px)]">Synthetic demonstration workspace</div>
      </div>
    </div>
  )
}
