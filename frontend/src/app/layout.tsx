import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { BRAND } from "@/components/brand";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

const sans = Geist({ variable: "--font-geist-sans", subsets: ["latin", "cyrillic"], display: "swap" });
const mono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin", "cyrillic"], display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(BRAND.url),
  title: { default: "Норма — проверка сайта на соответствие законодательству РФ", template: "%s — Норма" },
  description:
    "Автоматический аудит сайта по 152-ФЗ, 149-ФЗ, закону о рекламе и защите прав потребителей. Вставьте URL — получите оценку рисков, нормативные основания и рекомендации.",
  applicationName: "Норма",
  keywords: ["проверка сайта 152-ФЗ", "аудит персональных данных", "политика конфиденциальности", "согласие на обработку персональных данных", "маркировка рекламы", "проверка интернет-магазина"],
  openGraph: { type: "website", locale: "ru_RU", siteName: "Норма", url: "/" },
  twitter: { card: "summary_large_image" },
  alternates: { canonical: "/" },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = { themeColor: "#060709", colorScheme: "dark" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ru" data-scroll-behavior="smooth" className={`${sans.variable} ${mono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        {/* Подложка на весь сайт: бронзовая Фемида, приглушена тёмным — для единого стиля, не мешает чтению */}
        <div aria-hidden className="pointer-events-none fixed inset-0 -z-10">
          <div className="absolute inset-0 bg-cover bg-center opacity-[0.085]" style={{ backgroundImage: "url(/hero.png)" }} />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_90%_70%_at_50%_28%,transparent,rgba(6,7,9,0.72))]" />
          <div className="absolute inset-x-0 top-0 h-48 bg-gradient-to-b from-bg via-bg/70 to-transparent" />
        </div>
        <SiteHeader />
        <main className="flex-1">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
