import { ExternalLink } from "lucide-react";
import type { Metadata } from "next";
import { DISCLAIMER } from "@/components/brand";
import { RiseWords } from "@/components/effects";
import { SEVERITY_RU } from "@/lib/format";
import { backend } from "@/lib/server";

export const metadata: Metadata = {
  title: "Методика и нормативная база",
  description: "Правила автоматического аудита сайтов, их нормативные основания в действующей редакции, порядок расчёта Score и финансовой экспозиции.",
  alternates: { canonical: "/methodology" },
};

type Data = {
  rules: { id: string; title: string; category: string; severity: string; version: number; effective_from: string; mode: string; basis: { label: string; edition: string; official_url: string }[] }[];
  acts: { id: string; title: string; edition: string; checked_at: string; official_url: string }[];
};

type SecMethod = {
  repo: string; note: string; counts: { s1: number; s2: number };
  skills: { name: string; category: string; mode: string; status: string; sources: { slug: string; url: string }[] }[];
};

export default async function MethodologyPage() {
  const data = await backend<Data>("/api/public/rules", 300);
  const sec = await backend<SecMethod>("/api/public/security-methodology", 300);
  const groups = new Map<string, Data["rules"]>();
  data?.rules.forEach((r) => groups.set(r.category, [...(groups.get(r.category) || []), r]));
  return (
    <div className="mx-auto max-w-5xl px-4 py-20 sm:px-6">
      <RiseWords as="h1" text="Методика и нормативная база" className="text-gradient text-[34px] font-semibold tracking-[-0.03em] sm:text-[46px]" />
      <div className="prose-legal mt-8 max-w-3xl">
        <p>Сервис открывает публичную часть сайта в браузере (до 20 страниц, глубина 2), выполняет JavaScript, не отправляет формы и не заходит в закрытые разделы. Из собранных данных формируется единый набор фактов: формы и поля, cookies, сетевые запросы, внешние сервисы, документы, реквизиты.</p>
        <p>Факты сопоставляются с правилами. Каждое правило опирается на конкретную норму, текст которой выгружен из официального источника — ИПС «Законодательство России» (pravo.gov.ru). Правило имеет версию и срок действия: при изменении закона создаётся новая версия, старая сохраняется, а результат аудита хранит, какая версия применялась.</p>
        <h2>Статусы и уверенность</h2>
        <ul>
          <li><b>Выполнено по признакам</b> — признаки выполнения найдены.</li>
          <li><b>Вероятно не выполнено</b> — найдены признаки невыполнения с учётом ограничений обхода.</li>
          <li><b>Требует внимания</b> — факт установлен, но вывод зависит от сведений, которых нет на сайте.</li>
          <li><b>Не удалось определить</b> — по публичной части сайта вывод невозможен. Это не нарушение.</li>
        </ul>
        <h2>Score</h2>
        <p>Score = 100 × Σ(вес × оценка) / Σ вес. Вес: критично — 10, высокий риск — 6, средний — 3, низкий — 1. Оценка: выполнено — 1, требует внимания — 0,5, вероятно не выполнено — 0. Пункты «не удалось определить» не учитываются. Score отражает только результаты автоматических проверок сервиса и не является официальной оценкой соответствия законодательству РФ.</p>
        <h2>Финансовая экспозиция</h2>
        <p>Сумма диапазонов санкций КоАП РФ только по пунктам «вероятно не выполнено»; одна часть статьи учитывается один раз. VERIFIED RANGE — санкция прямо соответствует требованию и тип субъекта определён по реквизитам; ESTIMATED RANGE — тип субъекта не определён или квалификация не однозначна; NOT DETERMINABLE — специальной санкции нет. Повторные составы не применяются. Это не прогноз штрафа.</p>
        <h2>Роль AI</h2>
        <p>AI получает факты, сработавшие правила и дословный текст норм и формулирует объяснение и рекомендацию. AI не может менять статусы, нормы и суммы; ответы со ссылками на нормы вне переданных, с денежными суммами или обещаниями гарантий отбрасываются.</p>
      </div>

      <h2 className="mt-14 text-[22px] font-semibold tracking-tight">Нормативные акты</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {data?.acts.map((a) => (
          <div key={a.id} className="panel rounded-2xl p-4">
            <div className="text-[14px] font-medium">{a.title}</div>
            <div className="mt-1 text-[12.5px] text-dim">{a.edition} · сверено {a.checked_at}</div>
            <a href={a.official_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-[12.5px] text-text underline decoration-line-3 underline-offset-4">pravo.gov.ru <ExternalLink className="size-3" /></a>
          </div>
        ))}
      </div>

      <h2 className="mt-14 text-[22px] font-semibold tracking-tight">Правила ({data?.rules.length ?? 0})</h2>
      {!data && <p className="mt-3 text-[13px] text-dim">Список правил временно недоступен.</p>}
      <div className="mt-4 space-y-8">
        {[...groups.entries()].map(([cat, rules]) => (
          <div key={cat}>
            <div className="mb-2 text-[12px] font-medium uppercase tracking-[0.14em] text-dim">{cat}</div>
            <div className="space-y-2">
              {rules.map((r) => (
                <div key={r.id} className="panel rounded-xl p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-[14px] font-medium">{r.title}</div>
                    <div className="font-mono text-[11.5px] text-dim">{r.id} · v{r.version} · {SEVERITY_RU[r.severity]}{r.mode === "ecommerce" ? " · E-COMMERCE" : ""}</div>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[12.5px]">
                    {r.basis.map((b) => (
                      <a key={b.label} href={b.official_url} target="_blank" rel="noopener noreferrer" className="text-muted underline decoration-line-3 underline-offset-4 hover:text-text">{b.label}</a>
                    ))}
                    <span className="text-dim">действует с {r.effective_from}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {sec && (
        <>
          <h2 className="mt-14 text-[22px] font-semibold tracking-tight">Проверка безопасности (платно)</h2>
          <p className="mt-3 max-w-3xl text-[14px] leading-relaxed text-muted">
            Модуль безопасности построен по методике OWASP ({sec.counts.s1} проверок работают на любом сайте, {sec.counts.s2} — только
            для сайтов, подтверждённых владельцем). Мы проверяем сайт так, как это видит обычный посетитель, и ничего не взламываем:
            не достаём данные из базы, не заходим в чужие аккаунты, не обходим капчу. Активные тесты (попытки взлома в безопасном
            режиме) запускаются только после того, как вы докажете, что сайт ваш.
          </p>
          <div className="mt-5 grid gap-2 sm:grid-cols-2">
            {sec.skills.map((s) => (
              <div key={s.name} className="panel flex items-center justify-between gap-3 rounded-xl p-4">
                <div>
                  <div className="text-[14px] font-medium">{s.name}</div>
                  <div className="text-[12px] text-dim">{s.category}</div>
                </div>
                <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[11.5px] ${s.mode === "S1" ? "border-ok/30 text-ok" : "border-line-2 text-dim"}`}>
                  {s.mode === "S1" ? "проверяется" : "по подтверждению домена"}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[12px] leading-relaxed text-dim">
            Методика основана на открытом наборе навыков OWASP. Проверка безопасности — информационный инструмент, не аудит по
            ГОСТ/PCI DSS и не пентест-отчёт.
          </p>
        </>
      )}

      <p className="mt-12 text-[12px] leading-relaxed text-dim">{DISCLAIMER}</p>
    </div>
  );
}
