"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ExternalLink, Info, Scale } from "lucide-react";
import * as React from "react";
import { rub, SEVERITY_RU, STATE_RU, STATUS } from "@/lib/format";
import type { AuditResult, Basis, Exposure, Result } from "@/lib/types";
import { CountUp } from "../effects";
import { Badge, Dialog, DialogContent, DialogTrigger, Dot, Label, Tip, cx } from "../ui";

export function ScoreRing({ score }: { score: number | null }) {
  const r = 54;
  const c = 2 * Math.PI * r;
  const v = score ?? 0;
  const color = score === null ? "var(--unk)" : v >= 80 ? "var(--ok)" : v >= 55 ? "var(--warn)" : "var(--risk)";
  return (
    <div className="relative size-[150px] shrink-0">
      <svg viewBox="0 0 128 128" className="size-full -rotate-90">
        <circle cx="64" cy="64" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
        <motion.circle cx="64" cy="64" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round" strokeDasharray={c}
          initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c - (c * v) / 100 }} transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
          style={{ filter: `drop-shadow(0 0 10px color-mix(in oklab, ${color} 50%, transparent))` }} />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="text-[44px] font-semibold leading-none tracking-tight tabular-nums">{score === null ? "—" : <CountUp value={v} />}</div>
          <div className="mt-1 text-[12px] text-dim">из 100</div>
        </div>
      </div>
    </div>
  );
}

export function ExposureCard({ exp }: { exp: Exposure }) {
  const has = exp.items.length > 0;
  const stateColor = exp.state === "VERIFIED_RANGE" ? "var(--ok)" : exp.state === "ESTIMATED_RANGE" ? "var(--warn)" : "var(--unk)";
  return (
    <div className="panel flex h-full flex-col rounded-2xl p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Label>Финансовая экспозиция</Label>
        <Badge color={stateColor}>{has ? STATE_RU[exp.state] : "Нет рассчитанных рисков"}</Badge>
      </div>
      <div className="mt-4 text-[34px] font-semibold leading-tight tracking-tight tabular-nums sm:text-[40px]">
        {has ? (
          <>
            <CountUp value={exp.min} format={rub} />
            <span className="text-dim"> – </span>
            <CountUp value={exp.max} format={rub} />
          </>
        ) : (
          "0 ₽"
        )}
      </div>
      <p className="mt-2 text-[13px] leading-relaxed text-muted">
        {has ? "Оценочный диапазон потенциальных финансовых последствий выявленных рисков." : "Пунктов «вероятно не выполнено» с установленной санкцией не найдено."}
      </p>
      {exp.potential.items.length > 0 && (
        <p className="mt-2 text-[12.5px] text-dim">
          Ещё {rub(exp.potential.min)} – {rub(exp.potential.max)} — по пунктам, требующим ручной проверки (в сумму не входит).
        </p>
      )}
      <div className="mt-auto flex flex-wrap items-center gap-4 pt-5 text-[12.5px]">
        <span className="inline-flex items-center gap-1.5 text-dim"><Info className="size-3.5" /> Это не гарантированный штраф.</span>
        <Dialog>
          <DialogTrigger className="cursor-pointer text-text underline decoration-line-3 underline-offset-4 hover:decoration-white">Как рассчитано?</DialogTrigger>
          <DialogContent title="Как рассчитана финансовая экспозиция" wide>
            <div className="space-y-4 text-[13.5px] leading-relaxed text-muted">
              <p>Сумма складывается из диапазонов штрафов КоАП РФ только по пунктам со статусом «вероятно не выполнено». Одна часть статьи учитывается один раз.</p>
              <p>Тип субъекта: <span className="text-text">{exp.subject_ru}</span>. Если ИП в части статьи не выделены отдельно, применяется диапазон для должностных лиц (примечание к ст. 2.4 КоАП РФ).</p>
              <div className="grid gap-2 text-[12.5px] sm:grid-cols-3">
                <div className="rounded-xl border border-line p-3"><b className="text-ok">VERIFIED RANGE</b><br />санкция прямо соответствует требованию, тип субъекта определён по реквизитам</div>
                <div className="rounded-xl border border-line p-3"><b className="text-warn">ESTIMATED RANGE</b><br />тип субъекта не определён или квалификация не однозначна</div>
                <div className="rounded-xl border border-line p-3"><b className="text-unk">NOT DETERMINABLE</b><br />специальной санкции нет — сумма не считается</div>
              </div>
              {[...exp.items.map((i) => ({ ...i, main: true })), ...exp.potential.items.map((i) => ({ ...i, main: false }))].map((i) => (
                <div key={i.rule_id + i.legal_basis} className="rounded-xl border border-line bg-panel-2/50 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-[12px] text-dim">{i.rule_id}</span>
                    <span className="font-medium text-text tabular-nums">{rub(i.min_value)} – {rub(i.max_value)}</span>
                  </div>
                  <div className="mt-1 text-[12.5px]">{i.calculation_method}</div>
                  <div className="mt-1 text-[12px] text-dim">{i.main ? "Входит в сумму" : "Потенциально, в сумму не входит"} · {STATE_RU[i.state]} · КоАП {i.date}</div>
                </div>
              ))}
              <p className="text-[12px] text-dim">{exp.note}</p>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

export function Counters({ counts, onPick, active }: { counts: AuditResult["counts"]; onPick: (s: string) => void; active: string }) {
  const items = [
    { k: "FAIL", n: counts.fail, label: "проблемы", c: "var(--risk)" },
    { k: "REVIEW", n: counts.review, label: "требуют внимания", c: "var(--warn)" },
    { k: "PASS", n: counts.pass, label: "проверок пройдено", c: "var(--ok)" },
    { k: "UNKNOWN", n: counts.unknown, label: "невозможно определить автоматически", c: "var(--unk)" },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map((i) => (
        <button key={i.k} onClick={() => onPick(active === i.k ? "ALL" : i.k)}
          className={cx("panel group rounded-2xl p-4 text-left transition-all", active === i.k ? "border-white/25" : "hover:border-line-2")}>
          <div className="flex items-center gap-2">
            <Dot color={i.c} />
            <span className="text-[28px] font-semibold tabular-nums tracking-tight">{i.n}</span>
          </div>
          <div className="mt-1 text-[12.5px] leading-snug text-muted">{i.label}</div>
        </button>
      ))}
    </div>
  );
}

export function NormDialog({ b }: { b: Basis }) {
  return (
    <Dialog>
      <DialogTrigger className="inline-flex cursor-pointer items-center gap-1 text-[12.5px] font-medium text-text underline decoration-line-3 underline-offset-4 hover:decoration-white">
        Открыть норму <span aria-hidden>→</span>
      </DialogTrigger>
      <DialogContent title={b.label} wide>
        <div className="space-y-4">
          <div className="text-[13px] text-muted">{b.title}</div>
          {b.text ? (
            <blockquote className="whitespace-pre-line rounded-xl border border-line bg-black/30 p-4 font-mono text-[12.5px] leading-relaxed text-muted">{b.text}</blockquote>
          ) : (
            <div className="rounded-xl border border-line p-4 text-[13px] text-dim">Дословный текст нормы доступен в полном отчёте.</div>
          )}
          <div className="grid gap-1 text-[12.5px] text-dim">
            <div>Редакция: <span className="text-muted">{b.edition}</span>{b.checked_at ? ` · сверено ${b.checked_at}` : ""}</div>
            {b.effective_from ? <div>Действует с: <span className="text-muted">{b.effective_from}</span></div> : null}
          </div>
          <a href={b.official_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-[13px] text-text underline decoration-line-3 underline-offset-4">
            Официальный источник — pravo.gov.ru <ExternalLink className="size-3.5" />
          </a>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function IssueCard({ r, ai, locked, defaultOpen }: { r: Result; ai?: { explanation?: string | null; recommendation?: string | null }; locked?: boolean; defaultOpen?: boolean }) {
  const [open, setOpen] = React.useState(!!defaultOpen);
  const st = STATUS[r.status];
  return (
    <motion.div layout initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className="panel overflow-hidden rounded-2xl">
      <button onClick={() => setOpen(!open)} className="flex w-full items-start gap-4 p-5 text-left" aria-expanded={open}>
        <span className="mt-1.5"><Dot color={st.color} /></span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em]" style={{ color: st.color }}>{r.category}</span>
            <span className="text-[11.5px] text-dim">{SEVERITY_RU[r.severity]}</span>
          </div>
          <div className="mt-1 text-[15.5px] font-medium leading-snug tracking-tight">{r.title}</div>
          <div className="mt-1.5 line-clamp-2 text-[13.5px] leading-relaxed text-muted">{r.fact}</div>
        </div>
        <div className="hidden shrink-0 flex-col items-end gap-2 sm:flex">
          <Badge color={st.color}>{st.label}</Badge>
          {r.finance?.min_value !== undefined && r.finance.bucket === "main" ? (
            <span className="font-mono text-[12px] text-dim">{rub(r.finance.min_value)} – {rub(r.finance.max_value)}</span>
          ) : null}
        </div>
        <ChevronDown className={cx("mt-1 size-4 shrink-0 text-dim transition-transform", open && "rotate-180")} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}>
            <div className="grid gap-5 border-t border-line px-5 pb-6 pt-5 md:grid-cols-[1fr_1fr]">
              <div className="space-y-5">
                <Field title="Статус">
                  <div className="text-[13.5px]" style={{ color: st.color }}>{r.status_ru}</div>
                  <div className="text-[12.5px] text-dim">Уверенность: {r.confidence_ru} · правило {r.rule_id} v{r.version}</div>
                </Field>
                <Field title="Нормативное основание">
                  <div className="space-y-2.5">
                    {r.basis.map((b) => (
                      <div key={b.id} className="rounded-xl border border-line bg-panel-2/40 p-3">
                        <div className="flex items-start gap-2 text-[13.5px] text-text"><Scale className="mt-0.5 size-3.5 shrink-0 text-dim" /> {b.label}</div>
                        <div className="mt-1 text-[12px] text-dim">{b.title} · {b.edition}</div>
                        <div className="mt-2"><NormDialog b={b} /></div>
                      </div>
                    ))}
                  </div>
                </Field>
                <Field title="Что найдено">
                  <p className="text-[13.5px] leading-relaxed text-muted">{r.fact}</p>
                  {locked ? (
                    <div className="mt-2 rounded-xl border border-dashed border-line-2 p-3 text-[12.5px] text-dim">Фрагменты кода и страницы-доказательства — в полном отчёте.</div>
                  ) : (
                    r.evidence.slice(0, 4).map((e, i) => (
                      <div key={i} className="mt-2">
                        {(e.label || e.page) && <div className="text-[12px] text-dim">{e.label}{e.page ? <> · <a href={e.page} target="_blank" rel="noopener noreferrer nofollow" className="underline decoration-line-3 underline-offset-2">{e.page.replace(/^https?:\/\//, "")}</a></> : null}</div>}
                        {e.snippet ? <pre className="mt-1 max-h-44 overflow-auto whitespace-pre-wrap break-all rounded-xl border border-line bg-black/40 p-3 font-mono text-[11.5px] leading-relaxed text-dim">{e.snippet}</pre> : null}
                      </div>
                    ))
                  )}
                </Field>
              </div>
              <div className="space-y-5">
                <Field title="Почему это важно">
                  <p className="text-[13.5px] leading-relaxed text-muted">{ai?.explanation || r.why}</p>
                  {ai?.explanation ? <div className="mt-1 text-[11.5px] text-dim">Сформулировано AI на основе фактов и текста нормы</div> : null}
                </Field>
                <Field title="Что сделать">
                  <p className="text-[13.5px] leading-relaxed text-text/90">{ai?.recommendation || r.fix}</p>
                </Field>
                {r.finance?.min_value !== undefined ? (
                  <Field title="Финансовая оценка">
                    <div className="text-[14px] font-medium tabular-nums">{rub(r.finance.min_value)} – {rub(r.finance.max_value)}</div>
                    <div className="mt-1 text-[12px] leading-relaxed text-dim">
                      {STATE_RU[r.finance.state]} · {r.finance.bucket === "main" ? "входит в экспозицию" : "потенциально, не входит в сумму"}. {r.finance.calculation_method}
                    </div>
                  </Field>
                ) : null}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function Field({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <Label className="mb-1.5">{title}</Label>
      {children}
    </div>
  );
}

export function TipIcon({ text }: { text: string }) {
  return (
    <Tip content={text}>
      <button className="text-dim hover:text-text" aria-label="Подсказка"><Info className="size-3.5" /></button>
    </Tip>
  );
}
