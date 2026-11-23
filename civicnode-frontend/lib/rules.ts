import type { DemoRule } from "@/types/civic"
import { apiRequest, DEMO_MODE } from "@/lib/api-client"
import { loadMockState, saveMockRules } from "@/lib/mock-data"

export async function listRules(): Promise<DemoRule[]> {
  return DEMO_MODE ? loadMockState().rules : apiRequest<DemoRule[]>("/api/rules")
}

export async function persistRules(rules: DemoRule[]): Promise<void> {
  if (DEMO_MODE) {
    saveMockRules(rules)
    return
  }
  await apiRequest<void>("/api/rules", { method: "PUT", body: JSON.stringify(rules) })
}
