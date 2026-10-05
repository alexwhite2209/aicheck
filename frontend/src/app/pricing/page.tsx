import { Check } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { DISCLAIMER } from "@/components/brand";
import { RiseWords, SlideIn } from "@/components/effects";
import { Button } from "@/components/ui";
import { rub } from "@/lib/format";
import { backend } from "@/lib/server";

export const metadata: Metadata = {
  title: "Тарифы",
  description: "Экспресс-проверка бесплатно. Полный аудит — 299 ₽: законодательство РФ, безопасность, реестры, финансовая экспозиция и PDF.",
  alternates: { canonical: "/pricing" },
};

export const dynamic = "force-dynamic"; // цены берём из базы на каждый заход (меняются в админке сразу)

type Prices = { payments_enabled: boolean; paywall: boolean; prices: { code: string; title: string; description: string; amount_rub: number }[] };

const FEATURES: Record<string, string[]> = {
  free: ["Базовая проверка соответствия законодательству РФ", "Score и все найденные проблемы", "Нормативные основания со ссылками", "Базовые рекомендации", "Без регистрации"],
  full_audit: ["Законодательство РФ: доказательства, тексты норм, AI-объяснения", "Security Skills: 10 пассивных проверок безопасности", "Реестры: домен, ЕГРЮЛ/ЕГРИП, реестр операторов ПД", "Финансовая экспозиция", "Полный PDF-отчёт"],
  recheck: ["Полный повторный аудит", "Сравнение с предыдущим результатом: что исправлено, что появилось", "История в личном кабинете"],
};

export default async function PricingPage() {
  const data = await backend<Prices>("/api/prices", 0);
  const prices = data?.prices ?? [];
  return (
    <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <RiseWords as="h1" text="Экспресс-проверка — бесплатно" className="text-gradient text-[34px] font-semibold tracking-[-0.03em] sm:text-[46px]" />
        <p className="mt-4 text-[15px] text-muted">Вход и регистрация — только логин и пароль. Платите только за подробный отчёт, когда нужно передать его разработчику или юристу.</p>
        {data && !data.paywall && <p className="mt-3 text-[13px] text-ok">Сейчас полный отчёт открыт бесплатно для всех проверок.</p>}
      </div>
      <div className="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <SlideIn from="left">
          <Plan title="Экспресс-проверка" price="0 ₽" desc="Базовая проверка соответствия законодательству РФ" features={FEATURES.free} cta={<Button asChild variant="secondary" className="w-full"><Link href="/">Проверить сайт</Link></Button>} />
        </SlideIn>
        {prices.map((p, i) => (
          <SlideIn key={p.code} from={i % 2 ? "right" : "left"} delay={0.05 * (i + 1)}>
            <Plan title={p.title} price={rub(p.amount_rub)} desc={p.description} features={FEATURES[p.code] || []} highlight={p.code === "full_audit"}
              cta={<Button asChild variant={p.code === "full_audit" ? "primary" : "secondary"} className="w-full"><Link href="/">{p.code === "full_audit" ? "Начать с проверки" : "Подробнее"}</Link></Button>} />
          </SlideIn>
        ))}
      </div>
      {!data && <p className="mt-6 text-center text-[13px] text-dim">Цены временно недоступны.</p>}
      <p className="mx-auto mt-12 max-w-3xl text-center text-[12px] leading-relaxed text-dim">Оплата через ЮKassa. {DISCLAIMER}</p>
    </div>
  );
}

function Plan({ title, price, desc, features, cta, highlight }: { title: string; price: string; desc: string; features: string[]; cta: React.ReactNode; highlight?: boolean }) {
  return (
    <div className={`panel flex h-full flex-col rounded-2xl p-6 ${highlight ? "border-beam border-white/20" : ""}`}>
      <div className="text-[14px] font-medium">{title}</div>
      <div className="mt-3 text-[32px] font-semibold tracking-tight tabular-nums">{price}</div>
      <p className="mt-2 min-h-10 text-[13px] text-muted">{desc}</p>
      <ul className="mt-5 flex-1 space-y-2">
        {features.map((f) => <li key={f} className="flex gap-2 text-[13px] text-muted"><Check className="mt-0.5 size-3.5 shrink-0 text-ok" /> {f}</li>)}
      </ul>
      <div className="mt-6">{cta}</div>
    </div>
  );
}
