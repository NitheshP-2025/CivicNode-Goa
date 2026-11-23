"use client"

import Link from "next/link"
import { zodResolver } from "@hookform/resolvers/zod"
import { motion } from "framer-motion"
import { ArrowLeft, ArrowRight, AudioLines, Check, CheckCircle2, FileText, MapPin, Mic, Plus, ShieldCheck, Trash2, UploadCloud } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { SiteHeader } from "@/components/shared/site-header"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useCivic } from "@/hooks/use-civic"
import { useT } from "@/hooks/use-translations"
import type { CivicClaim, ClaimDraft, Language } from "@/types/civic"
import { uploadClaimDocuments } from "@/lib/documents"
import { transcribeIncident } from "@/lib/voice"

const claimFormSchema = z.object({
  farmerName: z.string().trim().min(2, "Enter the farmer name."),
  phone: z.string().regex(/^[6-9]\d{9}$/, "Enter a valid 10-digit mobile number."),
  district: z.string().min(2, "Select a district."),
  taluka: z.string().min(2, "Select a taluka."),
  village: z.string().trim().min(2, "Enter a village."),
  surveyNumber: z.string().trim().min(1, "Enter a survey number."),
  subdivision: z.string().trim().min(1, "Enter a subdivision."),
  landArea: z.string().refine((value) => Number(value) > 0, "Enter a land area greater than zero."),
  areaUnit: z.enum(["hectares", "acres"]),
  ownership: z.string().min(2, "Select ownership information."),
  documents: z.array(z.string()).min(1, "Add at least one supporting document."),
  claimType: z.string().min(2, "Select a claim type."),
  scheme: z.enum(["Flood Relief", "Land Acquisition"]),
  incidentDate: z.string().min(1, "Choose the incident date."),
  incidentLocation: z.string().trim().min(2, "Enter the incident location."),
  incidentDescription: z.string().trim().min(10, "Add a little more detail (at least 10 characters)."),
  reliefRequested: z.string().refine((value) => Number(value) >= 0, "Enter a valid amount."),
})
type ClaimFormValues = z.infer<typeof claimFormSchema>
type UploadItem = { id: string; name: string; size: number; type: string; previewUrl: string; file: File }

const steps = ["claim.step1", "claim.step2", "claim.step3", "claim.step4", "claim.step5"] as const
const districts = ["North Goa", "South Goa"]
const talukas = ["Ponda", "Bicholim", "Sanguem", "Quepem", "Canacona", "Bardez", "Salcete", "Tiswadi"]
const fieldSets: (keyof ClaimFormValues)[][] = [
  ["farmerName", "phone", "district", "taluka", "village"],
  ["surveyNumber", "subdivision", "landArea", "areaUnit", "ownership"],
  ["documents"],
  ["claimType", "scheme", "incidentDate", "incidentLocation", "incidentDescription", "reliefRequested"],
]

function FieldInput({ id, label, error, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { id: string; label: string; error?: string }) {
  return <div><label htmlFor={id} className="field-label">{label}</label><Input id={id} className="h-11 rounded-lg border-[#dbe4de] bg-white" aria-invalid={!!error} {...props} />{error && <p className="mt-1 text-xs text-red-600" role="alert">{error}</p>}</div>
}

function FieldSelect({ id, label, error, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { id: string; label: string; error?: string; children: React.ReactNode }) {
  return <div><label htmlFor={id} className="field-label">{label}</label><select id={id} className="form-control" aria-invalid={!!error} {...props}>{children}</select>{error && <p className="mt-1 text-xs text-red-600" role="alert">{error}</p>}</div>
}

export function ClaimWizard({ operatorMode = false }: { operatorMode?: boolean }) {
  const t = useT()
  const { verifiedPhone, addClaim, notify, isDemo, language } = useCivic()
  const [step, setStep] = useState(0)
  const [files, setFiles] = useState<UploadItem[]>([])
  const [dragging, setDragging] = useState(false)
  const [recording, setRecording] = useState(false)
  const [voiceLanguage, setVoiceLanguage] = useState<Language>("en")
  const [transcriptConfirmed, setTranscriptConfirmed] = useState(false)
  const [declared, setDeclared] = useState(false)
  const [operatorName, setOperatorName] = useState("M. Kamat")
  const [operatorCenter, setOperatorCenter] = useState("Ponda CSC")
  const [submittedClaim, setSubmittedClaim] = useState<CivicClaim | null>(null)
  const [submitError, setSubmitError] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const filesRef = useRef<UploadItem[]>([])
  const audioChunksRef = useRef<Blob[]>([])
  const form = useForm<ClaimFormValues>({
    resolver: zodResolver(claimFormSchema),
    mode: "onTouched",
    defaultValues: {
      farmerName: "", phone: verifiedPhone, district: "North Goa", taluka: "Ponda", village: "",
      surveyNumber: "", subdivision: "1", landArea: "", areaUnit: "hectares", ownership: "Owner cultivator",
      documents: [], claimType: "Crop loss — flooding", scheme: "Flood Relief", incidentDate: "2026-07-18",
      incidentLocation: "", incidentDescription: "", reliefRequested: "0",
    },
  })
  const { register, trigger, setValue, handleSubmit, watch, formState: { errors, isSubmitting } } = form
  const values = watch()
  const progress = ((step + 1) / steps.length) * 100
  const localizeScheme = (scheme: string) => scheme === "Flood Relief" ? t("claim.floodRelief") : t("claim.landAcquisition")
  const localizeOwnership = (ownership: string) => ownership === "Tenant cultivator" ? t("claim.tenant") : ownership === "Co-owner" ? t("claim.coOwner") : t("claim.owner")
  const localizeClaimType = (claimType: string) => claimType === "Land acquisition" ? t("claim.landAcquisition") : claimType === "Crop loss — storm damage" ? t("claim.stormLoss") : t("claim.floodLoss")
  const estimate = useMemo(() => {
    const area = Number(values.landArea) || 0
    const eligibleArea = values.areaUnit === "acres" ? area * 0.404686 : area
    return Math.round(eligibleArea * 9800)
  }, [values.landArea, values.areaUnit])

  useEffect(() => { if (verifiedPhone) setValue("phone", verifiedPhone) }, [verifiedPhone, setValue])
  useEffect(() => { filesRef.current = files }, [files])
  useEffect(() => () => { filesRef.current.forEach((file) => URL.revokeObjectURL(file.previewUrl)); recorderRef.current?.stream.getTracks().forEach((track) => track.stop()) }, [])

  function acceptFiles(fileList: FileList | File[]) {
    const candidates = Array.from(fileList)
    const allowed = candidates.filter((file) => ["application/pdf", "image/jpeg", "image/png"].includes(file.type) && file.size <= 10 * 1024 * 1024)
    const additions = allowed.slice(0, Math.max(0, 5 - files.length)).map((file) => ({
      id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2, 7)}`,
      name: file.name,
      size: file.size,
      type: file.type,
      previewUrl: URL.createObjectURL(file),
      file,
    }))
    if (allowed.length !== candidates.length || additions.length !== allowed.length) notify(t("claim.invalidFiles"))
    const next = [...files, ...additions]
    setFiles(next)
    setValue("documents", next.map((item) => item.name), { shouldValidate: true })
  }

  function removeFile(id: string) {
    const removed = files.find((file) => file.id === id)
    if (removed) URL.revokeObjectURL(removed.previewUrl)
    const next = files.filter((file) => file.id !== id)
    setFiles(next)
    setValue("documents", next.map((item) => item.name), { shouldValidate: true })
  }

  async function nextStep() {
    if (step < 4) {
      const valid = await trigger(fieldSets[step])
      if (valid) setStep((value) => Math.min(4, value + 1))
    }
  }

  async function recordVoice() {
    if (recording) {
      recorderRef.current?.stop()
      return
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      notify(t("claim.voiceUnsupported"))
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      audioChunksRef.current = []
      recorder.ondataavailable = (event) => { if (event.data.size > 0) audioChunksRef.current.push(event.data) }
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        const audio = new Blob(audioChunksRef.current, { type: recorder.mimeType || "audio/webm" })
        void transcribeIncident(audio, voiceLanguage).then((result) => {
          setValue("incidentDescription", result.transcript, { shouldValidate: true, shouldDirty: true })
          setTranscriptConfirmed(true)
          notify(result.simulated ? t("claim.voiceDemoReady") : t("claim.voiceLiveReady"))
        }).catch(() => notify(t("claim.voiceError"))).finally(() => setRecording(false))
      }
      recorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch {
      notify(t("claim.voiceMicDenied"))
    }
  }

  async function submit(valuesToSubmit: ClaimFormValues) {
    if (!declared) {
      setSubmitError(t("claim.declarationRequired"))
      return
    }
    setSubmitError("")
    try {
      const documentRefs = await uploadClaimDocuments(files.map((file) => file.file))
      const draft: ClaimDraft = {
        ...valuesToSubmit,
        landArea: Number(valuesToSubmit.landArea),
        reliefRequested: Number(valuesToSubmit.reliefRequested) || estimate,
        documents: documentRefs.map((document) => document.fileName),
        documentRefs,
        ...(operatorMode ? { operatorName, operatorCenter } : {}),
      }
      const claim = await addClaim(draft)
      setSubmittedClaim(claim)
      notify(`${t("claim.success")} ${claim.id}`)
    } catch {
      setSubmitError(t("claim.submitError"))
    }
  }

  if (submittedClaim) {
    return <div className="min-h-screen bg-[#f7faf8]"><SiteHeader active={operatorMode ? "csc" : "farmer"} /><main className="app-container grid min-h-[calc(100vh-76px)] place-items-center py-12"><motion.section initial={{ opacity: 0, y: 12, scale: .98 }} animate={{ opacity: 1, y: 0, scale: 1 }} className="surface w-full max-w-[620px] p-7 text-center sm:p-10"><div className="mx-auto grid size-16 place-items-center rounded-2xl bg-[#e5f5e9] text-[#176534]"><CheckCircle2 className="size-8" /></div><div className="eyebrow mt-6">{operatorMode ? t("csc.title") : t("common.demo")}</div><h1 className="mt-3 text-3xl font-semibold tracking-[-.05em] text-[#173b28]">{t("claim.success")}</h1><p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-500">{t("claim.successBody")}</p><div className="mt-7 rounded-2xl border border-[#dcebe0] bg-[#f5faf6] p-5 text-left"><div className="text-[10px] font-bold uppercase tracking-[.15em] text-slate-400">{t("claim.claimId")}</div><div className="mt-1 text-2xl font-extrabold tracking-tight text-[#14532d]">{submittedClaim.id}</div><div className="mt-4 grid gap-3 border-t border-[#dcebe0] pt-4 text-xs sm:grid-cols-3"><div><div className="text-slate-400">{t("claim.scheme")}</div><div className="mt-1 font-bold text-slate-700">{localizeScheme(submittedClaim.scheme)}</div></div><div><div className="text-slate-400">{t("claim.status")}</div><div className="mt-1 font-bold text-slate-700">{t("status.statusSubmitted")}</div></div><div><div className="text-slate-400">{t("claim.submitted")}</div><div className="mt-1 font-bold text-slate-700">{new Intl.DateTimeFormat(language === "mr" ? "mr-IN" : "en-IN").format(new Date(submittedClaim.submittedAt))}</div></div></div></div><div className="mt-6 flex flex-wrap justify-center gap-3"><Link href={`/status/${submittedClaim.id}`} className="inline-flex h-11 items-center gap-2 rounded-xl bg-[#14532d] px-5 text-sm font-bold text-white hover:bg-[#166534]">{t("claim.track")}<ArrowRight className="size-4" /></Link><Link href="/" className="inline-flex h-11 items-center rounded-xl border border-[#d9e3dc] bg-white px-5 text-sm font-bold text-[#31543c]">{t("nav.home")}</Link></div><p className="mt-6 text-[10px] text-slate-400">{isDemo ? t("common.demo") : t("claim.backendConnected")} · {t("verify.simulated")}</p></motion.section></main></div>
  }

  return <div className="min-h-screen bg-[#f7faf8]"><SiteHeader active={operatorMode ? "csc" : "farmer"} /><main className="app-container max-w-[1060px] py-7 sm:py-10">
    {operatorMode && <div className="mb-5 flex flex-col gap-4 rounded-2xl border border-[#d9eadf] bg-[#edf7ef] p-4 sm:flex-row sm:items-center sm:justify-between"><div><div className="text-xs font-extrabold uppercase tracking-[.12em] text-[#14532d]">{t("csc.notice")}</div><p className="mt-1 text-xs text-[#607468]">{t("csc.noticeBody")}</p></div><div className="grid gap-3 sm:grid-cols-2"><label className="text-[10px] font-bold text-[#617468]">{t("csc.operator")}<Input value={operatorName} onChange={(event) => setOperatorName(event.target.value)} className="mt-1 h-9 w-full rounded-lg border-[#d5e4d9] bg-white text-xs" /></label><label className="text-[10px] font-bold text-[#617468]">{t("csc.center")}<Input value={operatorCenter} onChange={(event) => setOperatorCenter(event.target.value)} className="mt-1 h-9 w-full rounded-lg border-[#d5e4d9] bg-white text-xs" /></label></div></div>}
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4"><div><Link href={operatorMode ? "/csc" : "/"} className="mb-4 inline-flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-[#14532d]"><ArrowLeft className="size-4" />{operatorMode ? t("csc.back") : t("nav.home")}</Link><div className="eyebrow">{operatorMode ? t("csc.title") : t("common.demo")}</div><h1 className="mt-2 text-3xl font-semibold tracking-[-.055em] text-[#173b28] sm:text-4xl">{t("claim.title")}</h1><p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">{t("claim.intro")}</p></div><div className="rounded-xl border border-[#dfe9e2] bg-white px-3 py-2 text-xs font-semibold text-slate-500"><ShieldCheck className="mr-1 inline size-4 text-[#176534]" />{t("verify.simulated")}</div></div>
    <div className="surface overflow-hidden">
      <div className="border-b border-[#e7eee8] px-4 py-5 sm:px-7"><div className="mb-4 flex items-center justify-between text-xs"><span className="font-bold text-[#31543c]">{t(steps[step])}</span><span className="text-slate-400">{t("claim.stepCount", { current: step + 1, total: steps.length })}</span></div><div className="h-1.5 overflow-hidden rounded-full bg-[#edf2ee]"><motion.div className="h-full rounded-full bg-[#16a34a]" animate={{ width: `${progress}%` }} transition={{ duration: .3 }} /></div><div className="mt-5 grid grid-cols-5 gap-2">{steps.map((key, index) => <button key={key} type="button" onClick={() => index < step && setStep(index)} aria-current={step === index ? "step" : undefined} className="flex min-w-0 flex-col items-center gap-2 text-center"><span className={`grid size-8 place-items-center rounded-full border text-[11px] font-bold transition ${index < step ? "border-[#14532d] bg-[#14532d] text-white" : index === step ? "border-[#14532d] bg-[#e8f5eb] text-[#14532d]" : "border-[#e2e8e4] bg-white text-slate-400"}`}>{index < step ? <Check className="size-4" /> : index + 1}</span><span className={`hidden text-[10px] font-semibold sm:block ${index === step ? "text-[#14532d]" : "text-slate-400"}`}>{t(key)}</span></button>)}</div></div>
      <form onSubmit={handleSubmit(submit)} noValidate>
        <div className="min-h-[380px] p-4 sm:p-7">
          {step === 0 && <section><h2 className="text-lg font-bold text-slate-800">{t("claim.step1Title")}</h2><p className="mt-1 text-xs leading-5 text-slate-500">{t("claim.step1Body")}</p><div className="mt-6 grid gap-5 sm:grid-cols-2"><FieldInput id="farmerName" label={t("claim.name")} placeholder={t("claim.namePlaceholder")} error={errors.farmerName ? t("claim.validationRequired") : undefined} {...register("farmerName")} /><FieldInput id="phone" label={t("claim.phone")} type="tel" inputMode="numeric" maxLength={10} error={errors.phone ? t("claim.validationPhone") : undefined} {...register("phone")} /><FieldSelect id="district" label={t("claim.district")} error={errors.district ? t("claim.validationRequired") : undefined} {...register("district")}><option value="">{t("claim.select")}</option>{districts.map((district) => <option key={district}>{district}</option>)}</FieldSelect><FieldSelect id="taluka" label={t("claim.taluka")} error={errors.taluka ? t("claim.validationRequired") : undefined} {...register("taluka")}><option value="">{t("claim.select")}</option>{talukas.map((taluka) => <option key={taluka}>{taluka}</option>)}</FieldSelect><FieldInput id="village" label={t("claim.village")} placeholder={t("claim.villagePlaceholder")} error={errors.village ? t("claim.validationRequired") : undefined} {...register("village")} /></div></section>}
          {step === 1 && <section><h2 className="text-lg font-bold text-slate-800">{t("claim.step2Title")}</h2><p className="mt-1 text-xs leading-5 text-slate-500">{t("claim.step2Body")}</p><div className="mt-6 grid gap-5 sm:grid-cols-2"><FieldInput id="surveyNumber" label={t("claim.survey")} placeholder={t("claim.surveyPlaceholder")} error={errors.surveyNumber ? t("claim.validationRequired") : undefined} {...register("surveyNumber")} /><FieldInput id="subdivision" label={t("claim.subdivision")} placeholder={t("claim.subdivisionPlaceholder")} error={errors.subdivision ? t("claim.validationRequired") : undefined} {...register("subdivision")} /><FieldInput id="landArea" label={t("claim.area")} type="number" min="0.1" step="0.1" placeholder="0.0" error={errors.landArea ? t("claim.validationArea") : undefined} {...register("landArea")} /><FieldSelect id="areaUnit" label={t("claim.unit")} {...register("areaUnit")}><option value="hectares">{t("claim.hectares")}</option><option value="acres">{t("claim.acres")}</option></FieldSelect><FieldSelect id="ownership" label={t("claim.ownership")} error={errors.ownership ? t("claim.validationRequired") : undefined} {...register("ownership")}><option value="Owner cultivator">{t("claim.owner")}</option><option value="Tenant cultivator">{t("claim.tenant")}</option><option value="Co-owner">{t("claim.coOwner")}</option></FieldSelect><div className="flex items-end rounded-xl bg-[#f1f8f3] p-3 text-xs leading-5 text-[#587262]"><MapPin className="mr-2 mt-0.5 size-4 shrink-0 text-[#176534]" />{t("claim.landNote")}</div></div></section>}
          {step === 2 && <section><h2 className="text-lg font-bold text-slate-800">{t("claim.step3Title")}</h2><p className="mt-1 text-xs leading-5 text-slate-500">{t("claim.step3Body")}</p><div onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFiles(event.dataTransfer.files) }} className={`mt-6 rounded-2xl border-2 border-dashed p-6 text-center transition sm:p-8 ${dragging ? "border-[#16a34a] bg-[#f0faf2]" : "border-[#d5e3d9] bg-[#fbfdfb]"}`}>
              <input ref={fileInputRef} type="file" multiple accept="application/pdf,image/png,image/jpeg" className="sr-only" onChange={(event) => { if (event.target.files) acceptFiles(event.target.files); event.target.value = "" }} />
              <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-[#e6f4e9] text-[#176534]"><UploadCloud className="size-6" /></span><div className="mt-4 text-sm font-bold text-slate-800">{t("claim.upload")}</div><div className="mt-1 text-xs text-slate-500">{t("claim.uploadHelp")}</div><button type="button" onClick={() => fileInputRef.current?.click()} className="mt-4 inline-flex h-10 items-center gap-2 rounded-lg border border-[#d7e3da] bg-white px-4 text-xs font-bold text-[#31543c] hover:border-[#a4c9ad]"><Plus className="size-4" />{t("claim.chooseFiles")}</button><div className="mt-3 text-[10px] text-slate-400">{t("claim.uploadLimit")}</div>
            </div>
            {errors.documents && <p className="mt-2 text-xs text-red-600" role="alert">{t("claim.validationDocuments")}</p>}
            <div className="mt-4 grid gap-3 sm:grid-cols-2">{files.map((file) => <div key={file.id} className="flex items-center gap-3 rounded-xl border border-[#e1e9e3] bg-white p-3"><div className="grid size-11 shrink-0 place-items-center overflow-hidden rounded-lg bg-[#f0f6f1] text-[#176534]">{file.type.startsWith("image/") ? <img src={file.previewUrl} alt={t("claim.filePreview", { name: file.name })} className="size-full object-cover" /> : <FileText className="size-5" />}</div><div className="min-w-0 flex-1"><div className="truncate text-xs font-bold text-slate-700">{file.name}</div><div className="mt-1 text-[10px] text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB · {t("claim.readyDemo")}</div><div className="mt-2 h-1 overflow-hidden rounded-full bg-[#edf2ee]"><div className="h-full w-full rounded-full bg-[#16a34a]" /></div></div><button type="button" aria-label={`${t("claim.remove")} ${file.name}`} onClick={() => removeFile(file.id)} className="grid size-8 shrink-0 place-items-center rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-600"><Trash2 className="size-4" /></button></div>)}</div>
            {files.some((file) => file.type === "application/pdf") && <div className="mt-4 grid gap-3 sm:grid-cols-2">{files.filter((file) => file.type === "application/pdf").map((file) => <div key={file.id} className="overflow-hidden rounded-xl border border-[#e1e9e3] bg-white"><div className="border-b border-[#e8eee9] px-3 py-2 text-xs font-bold text-slate-600">{file.name}</div><iframe title={t("claim.filePreview", { name: file.name })} src={file.previewUrl} className="h-[260px] w-full bg-slate-50" /></div>)}</div>}
          </section>}
          {step === 3 && <section><h2 className="text-lg font-bold text-slate-800">{t("claim.step4Title")}</h2><p className="mt-1 text-xs leading-5 text-slate-500">{t("claim.step4Body")}</p><div className="mt-6 grid gap-5 sm:grid-cols-2"><FieldSelect id="claimType" label={t("claim.type")} {...register("claimType")}><option value="Crop loss — flooding">{t("claim.floodLoss")}</option><option value="Land acquisition">{t("claim.landAcquisition")}</option><option value="Crop loss — storm damage">{t("claim.stormLoss")}</option></FieldSelect><FieldSelect id="scheme" label={t("claim.scheme")} {...register("scheme")}><option value="Flood Relief">{t("claim.floodRelief")}</option><option value="Land Acquisition">{t("claim.landAcquisition")}</option></FieldSelect><FieldInput id="incidentDate" label={t("claim.date")} type="date" error={errors.incidentDate ? t("claim.validationRequired") : undefined} {...register("incidentDate")} /><FieldInput id="incidentLocation" label={t("claim.location")} placeholder={t("claim.locationPlaceholder")} error={errors.incidentLocation ? t("claim.validationRequired") : undefined} {...register("incidentLocation")} /><div className="sm:col-span-2"><label htmlFor="incidentDescription" className="field-label">{t("claim.description")}</label><Textarea id="incidentDescription" rows={4} placeholder={t("claim.descriptionPlaceholder")} className="min-h-[105px] rounded-lg border-[#dbe4de]" aria-invalid={!!errors.incidentDescription} {...register("incidentDescription")} />{errors.incidentDescription && <p className="mt-1 text-xs text-red-600" role="alert">{t("claim.validationDescription")}</p>}</div><div className="sm:col-span-2 rounded-2xl border border-[#e1eae3] bg-[#fbfdfb] p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><div className="text-sm font-bold text-slate-700">{t("claim.voice")}</div><p className="mt-1 text-xs leading-5 text-slate-500">{t("claim.voiceNote")}</p></div><div className="flex items-center gap-2"><select aria-label={t("claim.language")} value={voiceLanguage} onChange={(event) => setVoiceLanguage(event.target.value as Language)} className="form-control !min-h-9 !w-auto !text-xs"><option value="en">{t("common.english")}</option><option value="kok">{t("common.konkani")}</option><option value="mr">{t("common.marathi")}</option></select><button type="button" onClick={recordVoice} className={`inline-flex h-9 items-center gap-2 rounded-lg px-3 text-xs font-bold ${recording ? "bg-red-50 text-red-700" : "bg-[#14532d] text-white"}`}>{recording ? <AudioLines className="size-4 animate-pulse" /> : <Mic className="size-4" />}{recording ? t("claim.stop") : t("claim.record")}</button></div></div>{transcriptConfirmed && <div className="mt-3 rounded-lg bg-[#edf7ef] p-2 text-[10px] font-semibold text-[#45654d]">{t("claim.transcript")}</div>}</div><FieldInput id="reliefRequested" label={t("claim.amount")} type="number" min="0" step="1" error={errors.reliefRequested ? t("claim.validationAmount") : undefined} {...register("reliefRequested")} /><div className="flex items-end rounded-xl bg-[#f0f8f2] p-3 text-xs"><div><div className="text-slate-500">{t("claim.demoEstimate")}</div><div className="mt-1 text-lg font-extrabold text-[#176534]">₹{estimate.toLocaleString("en-IN")}</div></div><div className="ml-auto text-right text-[10px] leading-4 text-slate-400">{t("claim.rate")}</div></div></div></section>}
          {step === 4 && <section><h2 className="text-lg font-bold text-slate-800">{t("claim.reviewTitle")}</h2><p className="mt-1 text-xs leading-5 text-slate-500">{t("claim.reviewBody")}</p><div className="mt-5 grid gap-4 lg:grid-cols-2"><SummaryCard title={t("claim.personalSummary")} onEdit={() => setStep(0)} rows={[[t("claim.name"), values.farmerName], [t("claim.phone"), values.phone], [t("claim.district"), values.district], [t("claim.taluka"), values.taluka], [t("claim.village"), values.village]]} /><SummaryCard title={t("claim.landSummary")} onEdit={() => setStep(1)} rows={[[t("claim.survey"), `${values.surveyNumber}/${values.subdivision}`], [t("claim.area"), `${values.landArea} ${values.areaUnit === "hectares" ? t("claim.hectares") : t("claim.acres")}`], [t("claim.ownership"), localizeOwnership(values.ownership)]]} /><SummaryCard title={t("claim.documents")} onEdit={() => setStep(2)} rows={files.map((file, index) => [`${t("claim.document")} ${index + 1}`, file.name])} /><SummaryCard title={t("claim.incidentSummary")} onEdit={() => setStep(3)} rows={[[t("claim.scheme"), localizeScheme(values.scheme)], [t("claim.type"), localizeClaimType(values.claimType)], [t("claim.date"), values.incidentDate], [t("claim.location"), values.incidentLocation], [t("claim.amount"), `₹${(Number(values.reliefRequested) || estimate).toLocaleString("en-IN")}`]]} /></div><label className="mt-5 flex cursor-pointer items-start gap-3 rounded-xl border border-[#dce9df] bg-[#f7fbf8] p-4 text-xs leading-5 text-slate-600"><input type="checkbox" checked={declared} onChange={(event) => { setDeclared(event.target.checked); setSubmitError("") }} className="mt-0.5 size-4 accent-[#14532d]" /><span>{t("claim.declaration")}</span></label>{submitError && <p className="mt-2 text-xs text-red-600" role="alert">{submitError}</p>}<div className="mt-4 flex items-start gap-2 text-[10px] leading-5 text-slate-400"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-[#25814a]" />{t("claim.aiNotice")}</div></section>}
        </div>
        <div className="flex items-center justify-between border-t border-[#e7eee8] bg-[#fbfdfb] px-4 py-4 sm:px-7"><button type="button" onClick={() => setStep((value) => Math.max(0, value - 1))} disabled={step === 0} className="inline-flex h-10 items-center gap-2 rounded-lg px-3 text-xs font-bold text-slate-600 hover:bg-slate-100 disabled:opacity-40"><ArrowLeft className="size-4" />{t("claim.back")}</button>{step < 4 ? <button type="button" onClick={nextStep} className="inline-flex h-11 items-center gap-2 rounded-xl bg-[#14532d] px-5 text-sm font-bold text-white transition hover:bg-[#166534]">{t("claim.next")}<ArrowRight className="size-4" /></button> : <button type="submit" disabled={isSubmitting || !declared} className="inline-flex h-11 items-center gap-2 rounded-xl bg-[#14532d] px-5 text-sm font-bold text-white transition hover:bg-[#166534] disabled:cursor-not-allowed disabled:opacity-50"><CheckCircle2 className="size-4" />{isSubmitting ? t("common.loading") : t("claim.submit")}</button>}</div>
      </form>
    </div>
    <p className="mt-4 text-center text-[10px] text-slate-400">{t("claim.localFilesNote")}</p>
  </main></div>
}

function SummaryCard({ title, rows, onEdit }: { title: string; rows: (string | undefined)[][]; onEdit: () => void }) {
  const t = useT()
  return <div className="rounded-xl border border-[#e1e9e3] bg-white p-4"><div className="flex items-center justify-between"><h3 className="text-xs font-extrabold text-slate-700">{title}</h3><button type="button" onClick={onEdit} className="text-[10px] font-bold text-[#176534] hover:underline">{t("claim.edit")}</button></div><div className="mt-3 flex flex-col gap-2">{rows.length ? rows.map(([label, value], index) => <div key={`${label}-${index}`} className="flex justify-between gap-4 text-[11px]"><span className="shrink-0 text-slate-400">{label}</span><span className="text-right font-semibold text-slate-700">{value || "—"}</span></div>) : <div className="text-[11px] text-slate-400">—</div>}</div></div>
}
