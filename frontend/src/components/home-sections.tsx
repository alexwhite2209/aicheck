"use client";

import { motion } from "framer-motion";
import { Cookie, FileCheck2, FileText, Megaphone, ShieldCheck, ShoppingCart, UserRoundCheck, Globe2, ScanSearch, Scale, FileSearch, Sparkles } from "lucide-react";
import * as React from "react";
import { CountUp, SlideIn, TiltCard } from "./effects";
import { Badge, Dot, Label, cx } from "./ui";

export function ReportPreview() {
  return (
    <TiltCard className="panel mx-auto w-full max-w-4xl rounded-3xl p-1.5" max={5}>
      <div className="rounded-[20px] border border-line bg-bg-2/80 p-5 sm:p-7">
        <div className="mb-5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-[12px] text-dim">
            <span className="flex gap-1.5">
              <span className="size-2.5 rounded-full bg-white/10" />
              <span className="size-2.5 rounded-full bg-white/10" />
              <span className="size-2.5 rounded-full bg-white/10" />
            </span>
            <span className="ml-2 font-mono">norma / audit / example.ru</span>
          </div>
          <Badge className="border-line-2 text-dim">Пример отчёта · демо-данные</Badge>
        </div>
        <div className="grid gap-4 md:grid-cols-[1fr_1.25fr]">
          <div className="rounded-2xl border border-line bg-panel p-5">
            <Label>Ваш результат</Label>
            <div className="mt-3 flex items-end gap-2">
              <span className="text-6xl font-semibold tracking-tight tabular-nums">
                <CountUp value={78} />
              </span>
              <span className="mb-2 text-lg text-dim">/ 100</span>
            </div>
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
              <motion.div className="h-full rounded-full bg-gradient-to-r from-warn to-ok" initial={{ width: 0 }} whileInView={{ width: "78%" }} transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }} viewport={{ once: true }} />
            </div>
            <div className="mt-5 grid grid-cols-2 gap-2 text-[13px]">
              {[["var(--risk)", "3 проблемы"], ["var(--warn)", "4 внимание"], ["var(--ok)", "11 пройдено"], ["var(--unk)", "5 не определено"]].map(([c, t]) => (
                <div key={t} className="flex items-center gap-2 rounded-lg border border-line bg-panel-2/60 px-2.5 py-1.5 text-muted">
                  <Dot color={c} /> {t}
                </div>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-4">
            <div className="rounded-2xl border border-line bg-panel p-5">
              <div className="flex items-center justify-between">
                <Label>Финансовая экспозиция</Label>
                <Badge color="var(--ok)">VERIFIED RANGE</Badge>
              </div>
              <div className="mt-3 text-4xl font-semibold tracking-tight tabular-nums">30 000 – 60 000 ₽</div>
              <div className="mt-2 text-[12.5px] text-dim">ч. 3 ст. 13.11 КоАП РФ · юридическое лицо · это не гарантированный штраф</div>
            </div>
            <div className="rounded-2xl border border-line bg-panel p-5">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-risk">
                <Dot color="var(--risk)" /> Документы
              </div>
              <div className="mt-2 text-[15px] font-medium">Политика обработки персональных данных не найдена</div>
              <div className="mt-1 text-[13px] text-muted">Формы с полями «телефон» и «имя» на 3 страницах. Нормативное основание: 152-ФЗ, ст. 18.1, ч. 2.</div>
              <div className="mt-3 rounded-lg border border-line bg-black/40 px-3 py-2 font-mono text-[11.5px] text-dim">
                &lt;form&gt; &lt;input name=&quot;phone&quot; type=&quot;tel&quot;&gt; …
              </div>
            </div>
          </div>
        </div>
      </div>
    </TiltCard>
  );
}

const CHECKS = [
  { icon: UserRoundCheck, title: "Персональные данные", text: "Формы, поля ПД, специальные категории, передача данных во внешние обработчики.", law: "152-ФЗ" },
  { icon: FileCheck2, title: "Согласия", text: "Есть ли согласие, оформлено ли отдельно от оферты и рассылок, не отмечено ли заранее.", law: "152-ФЗ, ст. 9" },
  { icon: FileText, title: "Документы", text: "Политика обработки ПД, её доступность со страниц с формами, сведения о защите данных.", law: "152-ФЗ, ст. 18.1" },
  { icon: Cookie, title: "Cookies и аналитика", text: "Сколько cookie, какие системы аналитики и чьи они, есть ли уведомление и описание в политике.", law: "152-ФЗ" },
  { icon: Globe2, title: "Внешние сервисы", text: "Сервисы иностранных компаний, признаки трансграничной передачи и локализации.", law: "152-ФЗ, ст. 12, 18" },
  { icon: Megaphone, title: "Реклама", text: "Признаки рекламных размещений, пометка «реклама», идентификатор erid, согласие на рассылки.", law: "38-ФЗ" },
  { icon: ShoppingCart, title: "Интернет-магазин", text: "Сведения о продавце, оферта, доставка, оплата, сроки возврата — по Правилам продажи 2026 года.", law: "ЗоЗПП, ПП № 657" },
  { icon: ShieldCheck, title: "Безопасность и владелец", text: "HTTPS при передаче данных, сведения о владельце сайта, способы входа пользователей.", law: "149-ФЗ, 152-ФЗ" },
];

export function ChecksGrid() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {CHECKS.map((c, i) => (
        <SlideIn key={c.title} from={i % 4 < 2 ? "left" : "right"} delay={(i % 4) * 0.06} parallax={i % 2 ? 14 : 0}>
          <TiltCard className="panel group h-full rounded-2xl p-5" max={4}>
            <div className="mb-4 grid size-10 place-items-center rounded-xl border border-line-2 bg-panel-2 text-muted transition group-hover:text-text">
              <c.icon className="size-[18px]" />
            </div>
            <div className="text-[15px] font-medium tracking-tight">{c.title}</div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-muted">{c.text}</p>
            <div className="mt-4 font-mono text-[11px] text-dim">{c.law}</div>
          </TiltCard>
        </SlideIn>
      ))}
    </div>
  );
}

const STEPS = [
  { icon: ScanSearch, title: "Факты с сайта", text: "Браузер открывает сайт, выполняет JavaScript и фиксирует формы, cookies, запросы, документы и реквизиты." },
  { icon: Scale, title: "Нормативное правило", text: "Каждое правило опирается на конкретную статью, часть и пункт в редакции, сверенной с pravo.gov.ru." },
  { icon: FileSearch, title: "Проверка и доказательство", text: "Алгоритм ставит статус с уровнем уверенности и прикладывает найденный фрагмент страницы." },
  { icon: Sparkles, title: "AI-объяснение", text: "AI переводит результат на понятный язык. Он не придумывает законы, статьи и суммы — это запрещено правилами." },
];

export function Pipeline() {
  const [active, setActive] = React.useState(0);
  React.useEffect(() => {
    const t = setInterval(() => setActive((a) => (a + 1) % STEPS.length), 2600);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="relative grid gap-3 md:grid-cols-4">
      <div className="absolute left-0 right-0 top-[38px] hidden h-px md:block">
        <div className="hairline" />
        <motion.div className="absolute top-[-1px] h-[3px] w-24 rounded-full bg-gradient-to-r from-transparent via-white/70 to-transparent blur-[1px]"
          animate={{ left: `${(active / (STEPS.length - 1)) * 88}%` }} transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }} />
      </div>
      {STEPS.map((s, i) => (
        <SlideIn key={s.title} from="bottom" delay={i * 0.08}>
          <button onMouseEnter={() => setActive(i)} className={cx("panel relative h-full w-full rounded-2xl p-5 text-left transition-all duration-500", active === i ? "border-white/20" : "opacity-80")}>
            <div className={cx("relative z-10 mb-4 grid size-11 place-items-center rounded-xl border transition-all duration-500", active === i ? "border-white/30 bg-white text-black shadow-[0_0_30px_-4px_rgba(168,190,255,0.6)]" : "border-line-2 bg-panel-2 text-muted")}>
              <s.icon className="size-[18px]" />
            </div>
            <div className="font-mono text-[11px] text-dim">0{i + 1}</div>
            <div className="mt-1 text-[15px] font-medium tracking-tight">{s.title}</div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-muted">{s.text}</p>
          </button>
        </SlideIn>
      ))}
    </div>
  );
}

const STATUSES = [
  { c: "var(--ok)", t: "Выполнено по признакам", d: "Признаки выполнения требования найдены на сайте." },
  { c: "var(--risk)", t: "Вероятно не выполнено", d: "Найдены признаки невыполнения. Сумма считается только по таким пунктам." },
  { c: "var(--warn)", t: "Требует внимания", d: "Факт установлен, но оценка зависит от сведений, которых нет на сайте." },
  { c: "var(--unk)", t: "Не удалось определить", d: "По публичной части сайта вывод сделать нельзя. Это не нарушение." },
];

export function StatusLegend() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {STATUSES.map((s, i) => (
        <SlideIn key={s.t} from={i < 2 ? "left" : "right"} delay={(i % 2) * 0.08}>
          <div className="panel h-full rounded-2xl p-5">
            <div className="flex items-center gap-2 text-[14px] font-medium" style={{ color: s.c }}>
              <Dot color={s.c} /> {s.t}
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-muted">{s.d}</p>
          </div>
        </SlideIn>
      ))}
    </div>
  );
}
