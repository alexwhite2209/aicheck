import { Check, ExternalLink } from "lucide-react";
import Link from "next/link";
import type { SeoPage as T } from "@/lib/seo-content";
import { SOURCES } from "@/lib/seo-content";
import { BRAND, DISCLAIMER } from "./brand";
import { RiseWords, SlideIn, Spotlight } from "./effects";
import { UrlForm } from "./url-form";

export function SeoPage({ p }: { p: T }) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "WebPage", name: p.title, description: p.description, url: `${BRAND.url}/${p.slug}`, inLanguage: "ru" },
      { "@type": "FAQPage", mainEntity: p.faq.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })) },
    ],
  };
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <section className="noise relative overflow-hidden border-b border-line">
        <div className="bg-grid absolute inset-0" aria-hidden />
        <Spotlight />
        <div className="relative mx-auto max-w-4xl px-4 py-20 text-center sm:px-6">
          <nav className="mb-6 text-[12.5px] text-dim"><Link href="/" className="hover:text-text">Главная</Link> / <span className="text-muted">{p.h1}</span></nav>
          <RiseWords as="h1" text={p.h1} className="text-gradient text-[32px] font-semibold leading-tight tracking-[-0.03em] sm:text-[46px]" />
          <p className="mx-auto mt-5 max-w-2xl text-[15.5px] leading-relaxed text-muted">{p.lead}</p>
          <div className="mx-auto mt-8 max-w-2xl"><UrlForm size="md" /></div>
        </div>
      </section>
      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <h2 className="mb-8 text-[26px] font-semibold tracking-tight">Что проверяет сервис</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {p.checks.map((c, i) => (
            <SlideIn key={c.t} from={i % 2 ? "right" : "left"} delay={(i % 3) * 0.05}>
              <div className="panel h-full rounded-2xl p-5">
                <div className="flex items-center gap-2 text-[15px] font-medium"><Check className="size-4 text-ok" /> {c.t}</div>
                <p className="mt-2 text-[13.5px] leading-relaxed text-muted">{c.d}</p>
              </div>
            </SlideIn>
          ))}
        </div>
      </section>
      <section className="mx-auto max-w-6xl px-4 pb-10 sm:px-6">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="panel rounded-2xl p-6">
            <h2 className="text-[18px] font-semibold tracking-tight">Нормативная база</h2>
            <p className="mt-1 text-[13px] text-dim">Редакции сверены с официальным источником 03.10.2026</p>
            <ul className="mt-4 space-y-3">
              {p.norms.map((n) => (
                <li key={n.label} className="text-[13.5px]">
                  <a href={SOURCES[n.label]} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-text underline decoration-line-3 underline-offset-4">{n.label} <ExternalLink className="size-3" /></a>
                  <div className="text-muted">{n.text}</div>
                </li>
              ))}
            </ul>
            <Link href="/methodology" className="mt-5 inline-block text-[13px] text-text underline decoration-line-3 underline-offset-4">Полная методика и список правил →</Link>
          </div>
          <div className="panel rounded-2xl p-6">
            <h2 className="text-[18px] font-semibold tracking-tight">Частые вопросы</h2>
            <div className="mt-4 space-y-4">
              {p.faq.map((f) => (
                <div key={f.q}>
                  <div className="text-[14px] font-medium">{f.q}</div>
                  <p className="mt-1 text-[13.5px] leading-relaxed text-muted">{f.a}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
        <p className="mt-8 text-center text-[12px] leading-relaxed text-dim">{DISCLAIMER}</p>
      </section>
    </>
  );
}

export function seoMetadata(p: T) {
  return {
    title: p.title,
    description: p.description,
    alternates: { canonical: `/${p.slug}` },
    openGraph: { title: p.title, description: p.description, url: `/${p.slug}`, type: "website" as const, locale: "ru_RU" },
  };
}
