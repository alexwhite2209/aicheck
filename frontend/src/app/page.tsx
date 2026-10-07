import { Check, Lock, ScanLine, UserX } from "lucide-react";
import { BRAND, DISCLAIMER } from "@/components/brand";
import { RiseWords, SlideIn, Spotlight } from "@/components/effects";
import { ChecksGrid, Pipeline, ReportPreview, StatusLegend } from "@/components/home-sections";
import { UrlForm } from "@/components/url-form";

const ACTS = ["152-ФЗ «О персональных данных»", "149-ФЗ «Об информации…»", "38-ФЗ «О рекламе»", "Закон «О защите прав потребителей»", "ПП РФ № 657 — Правила продажи", "КоАП РФ"];

export default function Home() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "WebApplication", name: "Норма", url: BRAND.url, applicationCategory: "BusinessApplication", operatingSystem: "Web", inLanguage: "ru",
        description: "Автоматический аудит сайта на соответствие применимым требованиям законодательства РФ", offers: { "@type": "Offer", price: "0", priceCurrency: "RUB" } },
      { "@type": "Organization", name: "Норма", url: BRAND.url },
    ],
  };
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <section className="noise relative overflow-hidden">
        {/* Фон: бронзовая Фемида (весы «законы ↔ деньги»), приглушена тёмным наложением для читаемости */}
        <div aria-hidden className="absolute inset-0 bg-cover bg-center opacity-[0.42]"
          style={{ backgroundImage: "url(/hero.png)", maskImage: "radial-gradient(ellipse 85% 80% at 50% 44%, #000 42%, transparent 82%)", WebkitMaskImage: "radial-gradient(ellipse 85% 80% at 50% 44%, #000 42%, transparent 82%)" }} />
        {/* мягкое затемнение за заголовком — чтобы текст читался, но картинка оставалась видимой */}
        <div aria-hidden className="absolute inset-0 bg-[radial-gradient(ellipse_62%_38%_at_50%_32%,rgba(6,7,9,0.72),transparent_72%)]" />
        <div aria-hidden className="absolute inset-0 bg-bg/25" />
        <div aria-hidden className="absolute inset-x-0 bottom-0 h-56 bg-gradient-to-b from-transparent to-bg" />
        <div className="bg-grid absolute inset-0" aria-hidden />
        <div aria-hidden className="absolute left-1/2 top-[-280px] h-[560px] w-[900px] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(168,190,255,0.16),transparent)]" />
        <Spotlight />
        <div className="relative mx-auto max-w-6xl px-4 pb-16 pt-20 sm:px-6 sm:pt-28">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-line-2 bg-panel/70 px-3.5 py-1.5 text-[11.5px] font-medium uppercase tracking-[0.18em] text-muted backdrop-blur">
              <span className="size-1.5 rounded-full bg-ok shadow-[0_0_10px_var(--ok)]" />
              Российский AI-аудит сайта
            </div>
            <RiseWords as="h1" text="Проверьте сайт на соответствие применимым требованиям законодательства РФ." className="text-gradient text-[34px] font-semibold leading-[1.08] tracking-[-0.035em] sm:text-[54px]" />
            <SlideIn from="bottom" delay={0.35}>
              <p className="mx-auto mt-6 max-w-xl text-[15.5px] leading-relaxed text-muted">
                Вставьте адрес — сервис откроет сайт, соберёт факты и сопоставит их с нормами 152-ФЗ, 149-ФЗ, закона о рекламе и защите прав потребителей.
              </p>
            </SlideIn>
            <SlideIn from="bottom" delay={0.5} className="mx-auto mt-9 max-w-2xl">
              <UrlForm />
            </SlideIn>
            <div className="mt-1 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[13px] text-dim">
              <span className="inline-flex items-center gap-1.5"><Lock className="size-3.5" /> Без доступа к админке</span>
              <span className="inline-flex items-center gap-1.5"><ScanLine className="size-3.5" /> Анализ публичной части сайта</span>
              <span className="inline-flex items-center gap-1.5"><UserX className="size-3.5" /> Без регистрации</span>
            </div>
          </div>
          <SlideIn from="bottom" delay={0.2} className="mt-20" parallax={30}>
            <ReportPreview />
          </SlideIn>
        </div>
      </section>

      <section className="border-y border-line bg-bg-2/60">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-7 gap-y-3 px-4 py-6 text-[13px] text-dim sm:px-6">
          <span className="font-mono text-[11.5px] uppercase tracking-[0.16em] text-muted">Нормы сверены с pravo.gov.ru · 03.10.2026</span>
          {ACTS.map((a) => (
            <span key={a} className="inline-flex items-center gap-1.5"><Check className="size-3.5 text-ok" /> {a}</span>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
        <div className="mb-12 max-w-2xl">
          <div className="mb-3 font-mono text-[12px] uppercase tracking-[0.18em] text-dim">Что проверяем</div>
          <RiseWords as="h2" text="Требования, которые можно проверить по публичной части сайта" className="text-[28px] font-semibold leading-tight tracking-[-0.03em] sm:text-[38px]" />
          <p className="mt-4 text-[15px] leading-relaxed text-muted">Набор правил зависит от типа сайта и найденных функций: формы, аналитика, реклама, онлайн-продажи.</p>
        </div>
        <ChecksGrid />
      </section>

      <section id="how" className="relative mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
        <div className="mb-12 max-w-2xl">
          <div className="mb-3 font-mono text-[12px] uppercase tracking-[0.18em] text-dim">Как устроена проверка</div>
          <RiseWords as="h2" text="Факты → норма → проверка → доказательство → объяснение" className="text-[28px] font-semibold leading-tight tracking-[-0.03em] sm:text-[38px]" />
          <p className="mt-4 text-[15px] leading-relaxed text-muted">Для вас — один экран с результатом. Внутри — строгая система, где AI помогает сформулировать вывод, но не является источником закона.</p>
        </div>
        <Pipeline />
      </section>

      <section className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
        <div className="mb-12 max-w-2xl">
          <div className="mb-3 font-mono text-[12px] uppercase tracking-[0.18em] text-dim">Честные статусы</div>
          <RiseWords as="h2" text="Сервис не пишет «сайт нарушает закон», если это не следует из фактов" className="text-[28px] font-semibold leading-tight tracking-[-0.03em] sm:text-[38px]" />
        </div>
        <StatusLegend />
      </section>

      <section className="relative mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="panel noise relative overflow-hidden rounded-3xl px-6 py-14 text-center sm:px-14">
          <Spotlight size={700} />
          <div className="relative mx-auto max-w-2xl">
            <RiseWords as="h2" text="Узнайте, что исправить на сайте, за пару минут" className="text-[28px] font-semibold tracking-[-0.03em] sm:text-[36px]" />
            <p className="mt-3 text-[15px] text-muted">Базовая проверка бесплатна и не требует регистрации.</p>
            <div className="mt-8">
              <UrlForm size="md" />
            </div>
            <p className="mx-auto mt-4 max-w-xl text-[12px] leading-relaxed text-dim">{DISCLAIMER}</p>
          </div>
        </div>
      </section>
    </>
  );
}
