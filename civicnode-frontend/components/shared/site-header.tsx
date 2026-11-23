"use client"

import Link from "next/link"
import { ArrowUpRight, Leaf, Menu, ShieldCheck } from "lucide-react"
import { useState } from "react"
import { useT } from "@/hooks/use-translations"
import { useCivic } from "@/hooks/use-civic"
import type { Language } from "@/types/civic"

export function Brand({ light = false }: { light?: boolean }) {
  const t = useT()
  return (
    <Link href="/" className={`inline-flex items-center gap-2.5 ${light ? "text-white" : "text-[#14532d]"}`} aria-label={t("brand.home")}>
      <span className={`grid size-10 place-items-center rounded-xl ${light ? "bg-white/12" : "bg-[#e2f2e7]"}`}>
        <Leaf className="size-5" aria-hidden="true" />
      </span>
      <span className="flex flex-col leading-none">
        <span className={`text-[15px] font-extrabold tracking-[-.04em] ${light ? "text-white" : "text-[#173b28]"}`}>CivicNode <span className="font-medium">Goa</span></span>
        <span className={`mt-1 text-[9px] font-semibold uppercase tracking-[.16em] ${light ? "text-white/55" : "text-[#87968b]"}`}>{t("brand.tagline")}</span>
      </span>
    </Link>
  )
}

export function LanguageSelect({ compact = false }: { compact?: boolean }) {
  const { language, setLanguage } = useCivic()
  const t = useT()
  return (
    <label className="flex items-center gap-2 text-xs font-semibold text-slate-600">
      {!compact && <span className="sr-only">{t("nav.language")}</span>}
      <select aria-label={t("nav.language")} value={language} onChange={(event) => setLanguage(event.target.value as Language)} className="form-control !min-h-9 !w-auto !rounded-lg !border-transparent !bg-transparent !px-2 text-xs focus:!border-[#16a34a]">
        <option value="en">{t("common.english")}</option>
        <option value="kok">{t("common.konkani")}</option>
        <option value="mr">{t("common.marathi")}</option>
      </select>
    </label>
  )
}

export function RoleLinks({ active }: { active?: "farmer" | "csc" | "officer" | "department" }) {
  const t = useT()
  const roles = [
    { key: "farmer", label: t("roles.farmer"), href: "/" },
    { key: "csc", label: t("roles.csc"), href: "/csc" },
    { key: "officer", label: t("roles.officer"), href: "/cases" },
    { key: "department", label: t("roles.department"), href: "/dashboard" },
  ] as const
  return (
    <div className="hidden items-center rounded-xl border border-[#e5ece7] bg-white p-1 lg:flex" aria-label={t("roles.switch")}>
      {roles.map((role) => (
        <Link key={role.key} href={role.href} aria-current={active === role.key ? "page" : undefined} className={`rounded-lg px-3 py-2 text-[11px] font-semibold transition ${active === role.key ? "bg-[#e7f5eb] text-[#14532d]" : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"}`}>
          {role.label}
        </Link>
      ))}
    </div>
  )
}

export function SiteHeader({ active = "farmer" }: { active?: "farmer" | "csc" }) {
  const t = useT()
  const [open, setOpen] = useState(false)
  return (
    <header className="relative z-30 border-b border-[#e9efeb] bg-white/90 backdrop-blur-xl">
      <div className="app-container flex h-[76px] items-center justify-between gap-4">
        <Brand />
        <nav className="hidden items-center gap-7 xl:flex" aria-label="Main navigation">
          <Link href="/" className="text-sm font-medium text-slate-600 hover:text-[#14532d]">{t("nav.home")}</Link>
          <a href="/#how-it-works" className="text-sm font-medium text-slate-600 hover:text-[#14532d]">{t("nav.how")}</a>
          <a href="/#schemes" className="text-sm font-medium text-slate-600 hover:text-[#14532d]">{t("nav.schemes")}</a>
          <a href="/#help" className="text-sm font-medium text-slate-600 hover:text-[#14532d]">{t("nav.help")}</a>
        </nav>
        <div className="hidden items-center gap-3 lg:flex">
          <RoleLinks active={active} />
          <LanguageSelect />
          <Link href="/verify" className="inline-flex h-10 items-center gap-2 rounded-xl bg-[#14532d] px-4 text-sm font-bold text-white shadow-sm transition hover:bg-[#166534] hover:shadow-md">
            <ShieldCheck className="size-4" aria-hidden="true" />{t("nav.apply")}<ArrowUpRight className="size-4 opacity-75" aria-hidden="true" />
          </Link>
        </div>
        <div className="flex items-center gap-2 lg:hidden">
          <LanguageSelect compact />
          <button type="button" aria-label={t("nav.open")} aria-expanded={open} onClick={() => setOpen(!open)} className="grid size-10 place-items-center rounded-xl border border-[#e5ece7] bg-white text-[#14532d]">
            <Menu className="size-5" />
          </button>
        </div>
      </div>
      {open && <nav className="absolute inset-x-0 top-full border-b border-[#e5ece7] bg-white p-4 shadow-lg lg:hidden" aria-label="Mobile navigation">
        <div className="app-container flex flex-col gap-2">
          <Link className="rounded-lg px-3 py-2 text-sm font-medium" href="/">{t("nav.home")}</Link>
          <a className="rounded-lg px-3 py-2 text-sm font-medium" href="/#how-it-works" onClick={() => setOpen(false)}>{t("nav.how")}</a>
          <a className="rounded-lg px-3 py-2 text-sm font-medium" href="/#schemes" onClick={() => setOpen(false)}>{t("nav.schemes")}</a>
          <a className="rounded-lg px-3 py-2 text-sm font-medium" href="/#help" onClick={() => setOpen(false)}>{t("nav.help")}</a>
          <div className="grid grid-cols-2 gap-2 border-t border-[#edf1ee] pt-3" aria-label={t("roles.switch")}>
            <Link className="rounded-lg bg-[#f3f8f4] px-3 py-2 text-xs font-semibold text-[#14532d]" href="/">{t("roles.farmer")}</Link>
            <Link className="rounded-lg bg-[#f3f8f4] px-3 py-2 text-xs font-semibold text-[#14532d]" href="/csc">{t("roles.csc")}</Link>
            <Link className="rounded-lg bg-[#f3f8f4] px-3 py-2 text-xs font-semibold text-[#14532d]" href="/cases">{t("roles.officer")}</Link>
            <Link className="rounded-lg bg-[#f3f8f4] px-3 py-2 text-xs font-semibold text-[#14532d]" href="/dashboard">{t("roles.department")}</Link>
          </div>
          <Link className="rounded-lg bg-[#14532d] px-3 py-2 text-sm font-semibold text-white" href="/verify">{t("nav.apply")}</Link>
        </div>
      </nav>}
    </header>
  )
}
