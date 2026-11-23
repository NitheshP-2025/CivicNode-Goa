import { ReceiptView } from "@/components/officer/receipt-view"

export default async function ReceiptPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <ReceiptView id={decodeURIComponent(id)} />
}
