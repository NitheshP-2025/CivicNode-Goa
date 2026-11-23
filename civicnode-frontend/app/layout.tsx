import type { Metadata, Viewport } from "next"
import { Analytics } from "@vercel/analytics/next"
import { CivicProvider } from "@/hooks/use-civic"
import "./globals.css"

export const metadata: Metadata = {
  title: {
    default: "CivicNode Goa | Transparent Relief, Faster Decisions",
    template: "%s · CivicNode Goa",
  },
  description: "A connected demonstration platform for disaster-relief claims, evidence review and accountable officer decisions in Goa.",
  applicationName: "CivicNode Goa",
  generator: "Next.js",
  keywords: ["disaster relief", "Goa", "claim tracking", "public service", "demonstration"],
}

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#14532D",
  width: "device-width",
  initialScale: 1,
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body className="antialiased">
        <CivicProvider>{children}</CivicProvider>
        {process.env.NODE_ENV === "production" && <Analytics />}
      </body>
    </html>
  )
}
