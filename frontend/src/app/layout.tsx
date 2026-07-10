import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { FramerProvider } from "@/components/framer-provider";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { ObservabilityProvider } from "@/observability/provider";
import { siteOrigin } from "@/lib/site";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const SITE_DESCRIPTION =
  "Deterministic, evidence-based engineering reports from any GitHub profile. Six signals, one hundred points, zero hallucinations.";

export const metadata: Metadata = {
  metadataBase: new URL(siteOrigin()),
  title: "Skill Issue — your GitHub, read honestly",
  description: SITE_DESCRIPTION,
  openGraph: {
    title: "Skill Issue — your GitHub, read honestly",
    description: SITE_DESCRIPTION,
    url: "/",
    siteName: "Skill Issue",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Skill Issue — your GitHub, read honestly",
    description: SITE_DESCRIPTION,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#09090b",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <SiteHeader />
        <ObservabilityProvider>
          <FramerProvider>{children}</FramerProvider>
        </ObservabilityProvider>
        <SiteFooter />
      </body>
    </html>
  );
}
