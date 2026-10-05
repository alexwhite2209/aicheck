"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Globe, ShieldCheck } from "lucide-react";
import * as React from "react";
import type { Registries, SecFinding, SecurityBlock } from "@/lib/types";
import { CountUp } from "../effects";
import { Badge, Dot, Label, cx } from "../ui";
import { NormDialog } from "./result-parts";

const SEV: Record<string, { ru: string; color: string }> = {
  critical: { ru: "Критично", color: "var(--risk)" },
  high: { ru: "Высокий риск", color: "var(--risk)" },
  medium: { ru: "Средний", color: "var(--warn)" },
  low: { ru: "Низкий", color: "var(--warn)" },
  info: { ru: "Факт", color: "var(--unk)" },
};
const ST: Record<string, { ru: string; color: string }> = {
  FAIL: { ru: "Проблема", color: "var(--risk)" },
  REVIEW: { ru: "Требует внимания", color: "var(--warn)" },
  PASS: { ru: "Пройдено", color: "var(--ok)" },
  INFO: { ru: "Информация", color: "var(--unk)" },
};

export function SecurityPanel({ security, registries }: { security: SecurityBlock; registries: Registries | null }) {
  const s = security;
  const score = s.score;
  const color = score === null ? "var(--unk)" : score >= 80 ? "var(--ok)" : score >= 55 ? "var(--warn)" : "var(--risk)";
  return (
    <section className="mt-14">
      <div className="mb-4 flex items-center gap-2">
        <ShieldCheck className="size-5 text-muted" />
        <h2 className="text-[20px] font-semibold tracking-tight">Безопасность сайта</h2>
        <Badge className="border-line-2 text-dim">Security Skills · в полном аудите</Badge>
      </div>

      <div className="panel grid gap-5 rounded-2xl p-6 sm:grid-cols-[auto_1fr]">
        <div className="flex items-center gap-4">
          <div className="grid size-[92px] place-items-center rounded-2xl border border-line" style={{ background: `color-mix(in oklab, ${color} 8%, transparent)` }}>
            <div className="text-center">
              <div className="text-[30px] font-semibold tabular-nums" style={{ color }}>{score === null ? "—" : <CountUp value={score} />}</div>
              <div className="text-[10px] text-dim">Security score</div>
            </div>
          </div>
        </div>
        <div className="flex flex-col justify-center gap-2">
          <div className="flex flex-wrap gap-2 text-[13px]">
            <Badge color="var(--risk)">{s.counts.fail} проблем</Badge>
            <Badge color="var(--warn)">{s.counts.review} внимание</Badge>
            <Badge color="var(--ok)">{s.counts.pass} пройдено</Badge>
          </div>
          <p className="text-[12.5px] leading-relaxed text-dim">{s.disclaimer}</p>
        </div>
      </div>

      <>
          <div className="mt-4 space-y-3">
            {s.findings.filter((f) => f.status !== "PASS").map((f) => <SecCard key={f.id} f={f} />)}
            {s.findings.filter((f) => f.status !== "PASS").length === 0 && (
              <div className="panel rounded-2xl p-6 text-center text-[14px] text-muted">Проблем безопасности на проверенных страницах не найдено.</div>
            )}
          </div>
          {registries && <RegistriesCard r={registries} />}
      </>
    </section>
  );
}

function SecCard({ f }: { f: SecFinding }) {
  const [open, setOpen] = React.useState(false);
  const st = ST[f.status];
  return (
    <motion.div layout className="panel overflow-hidden rounded-2xl">
      <button onClick={() => setOpen(!open)} className="flex w-full items-start gap-4 p-5 text-left">
        <span className="mt-1.5"><Dot color={st.color} /></span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em]" style={{ color: st.color }}>{f.category}</span>
            <span className="text-[11.5px] text-dim">{SEV[f.severity]?.ru} · {f.skill}</span>
            {f.touches_pd && <Badge className="border-line-2 text-dim">затрагивает ПД</Badge>}
          </div>
          <div className="mt-1 text-[15.5px] font-medium leading-snug tracking-tight">{f.title}</div>
          <div className="mt-1.5 line-clamp-2 text-[13.5px] leading-relaxed text-muted">{f.fact}</div>
          {f.tech && <div className="mt-1 font-mono text-[11px] text-dim/80">Технически: {f.tech}</div>}
        </div>
        <Badge color={st.color} className="hidden shrink-0 sm:inline-flex">{st.ru}</Badge>
        <ChevronDown className={cx("mt-1 size-4 shrink-0 text-dim transition-transform", open && "rotate-180")} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
            <div className="space-y-4 border-t border-line px-5 pb-6 pt-5">
              <Field title="Что найдено"><p className="text-[13.5px] leading-relaxed text-muted">{f.fact}</p></Field>
              {f.evidence.length > 0 && (
                <Field title="Доказательства">
                  {f.evidence.map((e, i) => (
                    <div key={i} className="mt-1.5">
                      {(e.label || e.page) && <div className="text-[12px] text-dim">{e.label}{e.page ? ` · ${e.page}` : ""}</div>}
                      {e.snippet && <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-all rounded-lg border border-line bg-black/40 p-2.5 font-mono text-[11.5px] text-dim">{e.snippet}</pre>}
                    </div>
                  ))}
                </Field>
              )}
              {f.legal_basis && (
                <Field title="Связь с законом">
                  <p className="text-[13px] leading-relaxed text-muted">{f.legal_note}</p>
                  <div className="mt-2 rounded-xl border border-line bg-panel-2/40 p-3">
                    <div className="text-[13.5px] text-text">{f.legal_basis.label}</div>
                    <div className="mt-2"><NormDialog b={f.legal_basis} /></div>
                  </div>
                </Field>
              )}
              <Field title="Что сделать"><p className="text-[13.5px] leading-relaxed text-text/90">{f.recommendation}</p></Field>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function RegistriesCard({ r }: { r: Registries }) {
  const d = r.domain;
  const e = r.egrul;
  return (
    <div className="panel mt-4 rounded-2xl p-6">
      <div className="mb-4 flex items-center gap-2 text-[15px] font-medium"><Globe className="size-4 text-dim" /> Проверка по реестрам</div>
      <div className="grid gap-4 md:grid-cols-3">
        <RegBox title="Домен">
          {d.registered ? (
            <ul className="space-y-1 text-[13px] text-muted">
              <li>Зарегистрирован: <span className="text-text">{d.created || "—"}</span></li>
              {d.age_years != null && <li>Возраст: <span className="text-text">{d.age_years} лет</span></li>}
              <li>Регистратор: <span className="text-text">{d.registrar || "—"}</span></li>
              <li>Оплачен до: <span className="text-text">{d.expires || "—"}</span></li>
            </ul>
          ) : (
            <p className="text-[13px] text-dim">{d.note}{d.link ? <> <a href={d.link} target="_blank" rel="noopener noreferrer" className="underline">проверить</a></> : null}</p>
          )}
        </RegBox>
        <RegBox title="ЕГРЮЛ / ЕГРИП">
          {e.found ? (
            <ul className="space-y-1 text-[13px] text-muted">
              <li className="text-text">{e.name}</li>
              <li>{e.kind} · {e.status}</li>
              <li>ОГРН: {e.ogrn}</li>
            </ul>
          ) : (
            <p className="text-[13px] text-dim">{e.note}{e.link ? <> <a href={e.link} target="_blank" rel="noopener noreferrer" className="underline">egrul.nalog.ru</a></> : null}</p>
          )}
        </RegBox>
        <RegBox title="Реестры Роскомнадзора">
          <ul className="space-y-2 text-[12.5px]">
            {(r.rkn?.registries || []).map((x) => (
              <li key={x.id}>
                <a href={x.link} target="_blank" rel="noopener noreferrer" className="text-text underline decoration-line-3 underline-offset-2">{x.title}</a>
                {x.captcha && <span className="ml-1 text-dim">(с капчей)</span>}
                <div className="text-dim">{x.why}</div>
              </li>
            ))}
          </ul>
        </RegBox>
      </div>
      <p className="mt-4 text-[12px] leading-relaxed text-dim">{r.rkn?.note} {r.note}</p>
    </div>
  );
}

function RegBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-panel-2/40 p-4">
      <Label className="mb-2">{title}</Label>
      {children}
    </div>
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
