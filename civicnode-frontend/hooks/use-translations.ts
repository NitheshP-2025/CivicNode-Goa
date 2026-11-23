"use client"

import en from "@/locales/en.json"
import kok from "@/locales/kok.json"
import mr from "@/locales/mr.json"
import { useCivic } from "@/hooks/use-civic"

const dictionaries = { en, kok, mr }
type TranslationKey = keyof typeof en

export function useT() {
  const { language } = useCivic()
  const dictionary = dictionaries[language]
  return (key: TranslationKey, values?: Record<string, string | number>) => {
    let result: string = dictionary[key] ?? en[key] ?? key
    if (values) {
      for (const [name, value] of Object.entries(values)) {
        result = result.replaceAll(`{${name}}`, String(value))
      }
    }
    return result
  }
}
