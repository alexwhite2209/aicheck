"use client";

import { motion } from "framer-motion";
import { ArrowRight, Download, RotateCw, Save, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { api, ApiError } from "@/lib/api";
import { dt, rub } from "@/lib/format";
import type { AuditResult, Comparison, StatusResp } from "@/lib/types";
import { DISCLAIMER } from "../brand";
import { Magnetic, Spotlight } from "../effects";
import { Badge, Button, Label, cx } from "../ui";
import { FactsPanels } from "./facts-panels";
import { Progress } from "./progress";
import { Counters, ExposureCard, IssueCard, ScoreRing } from "./result-parts";
import { SecurityPanel } from "./security-panel";

const CATEGORIES = ["Персональные данные", "Cookies", "Согласия", "Документы", "Реклама", "Потребители", "Интернет-магазин", "Информационная безопасность", "Внешние сервисы", "Технические требования"];

export function AuditView({ id }: { id: string }) {
  const [status, setStatus] = React.useState<StatusResp | null>(null);
  const [result, setResult] = React.useState<AuditResult | null>(null);
  const [error, setError] = React.useState("");
  const [started] = React.useState(() => Date.now());
  const router = useRouter();
  const params = useSearchParams();

  React.useEffect(() => {
    let stop = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const s = await api<StatusResp>(`/api/audit/${id}/status`);
        if (stop) return;
        setStatus(s);
        if (s.status === "done") {
          setResult(await api<AuditResult>(`/api/audit/${id}/result`));
          return;
        }
        if (s.status === "failed") return;
        timer = setTimeout(tick, 1100);
      } catch (e) {
        if (stop) return;
        if (e instanceof ApiError && e.status === 404) setError("Проверка не найдена");
        else timer = setTimeout(tick, 2500);
      }
    };
    tick();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [id]);

  // возврат с оплаты
  const handledPayment = React.useRef("");
  React.useEffect(() => {
    const pid = params.get("payment");
    if (!pid || !result || handledPayment.current === pid) return;
    let n = 0;
    const t = setInterval(async () => {
      n++;
      try {
        const p = await api<{ status: string; audit_id: string | null }>(`/api/payments/${pid}/status`);
        if (p.status === "succeeded") {
          clearInterval(t);
          handledPayment.current = pid;
          // «Повторная проверка» запускает новую проверку — переходим на неё
          if (p.audit_id && p.audit_id !== id) router.push(`/audit/${p.audit_id}`);
          else setResult(await api<AuditResult>(`/api/audit/${id}/result`));
        }
      } catch {}
      if (n > 20) clearInterval(t);
    }, 2000);
    return () => clearInterval(t);
  }, [params, result, id, router]);

  if (error) return <Centered title={error} action={<Button asChild variant="primary"><Link href="/">Новая проверка</Link></Button>} />;
  if (!status)
    return (
      <div className="mx-auto max-w-6xl animate-pulse px-4 py-10 sm:px-6">
        <div className="h-4 w-48 rounded bg-white/[0.06]" />
        <div className="mt-3 h-7 w-80 max-w-full rounded bg-white/[0.06]" />
        <div className="mt-8 grid gap-4 lg:grid-cols-2">
          <div className="panel h-44 rounded-2xl" />
          <div className="panel h-44 rounded-2xl" />
        </div>
      </div>
    );
  if (status.status === "failed")
    return (
      <Centered
        title="Не удалось проверить сайт"
        text={status.error || "Попробуйте ещё раз позже."}
        action={<Button variant="primary" onClick={() => router.push("/")}><RotateCw className="size-4" /> Проверить другой адрес</Button>}
      />
    );
  if (status.status !== "done" || !result) return <Progress url={status.url} stages={status.stages} startedAt={started} />;
  return <ResultScreen r={result} onUpdate={setResult} />;
}

function Centered({ title, text, action }: { title: string; text?: string; action?: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-lg px-4 py-28 text-center">
      <h1 className="text-[26px] font-semibold tracking-tight">{title}</h1>
      {text && <p className="mt-3 text-[14.5px] text-muted">{text}</p>}
      <div className="mt-8 flex justify-center">{action}</div>
    </div>
  );
}

function ResultScreen({ r, onUpdate }: { r: AuditResult; onUpdate: (r: AuditResult) => void }) {
  const [filter, setFilter] = React.useState("ALL");
  const [cat, setCat] = React.useState("ALL");
  const [msg, setMsg] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [prices, setPrices] = React.useState<{ payments_enabled: boolean; prices: { code: string; title: string; description: string; amount_rub: number }[] } | null>(null);
  const [receiptEmail, setReceiptEmail] = React.useState("");
  const router = useRouter();
  React.useEffect(() => {
    api<typeof prices>("/api/prices").then(setPrices).catch(() => {});
  }, []);
  const priceOf = (code: string) => prices?.prices.find((p) => p.code === code);
  const issues = r.results.filter((x) => x.status === "FAIL" || x.status === "REVIEW");
  const unknown = r.results.filter((x) => x.status === "UNKNOWN");
  const passed = r.results.filter((x) => x.status === "PASS");
  const cats = CATEGORIES.filter((c) => r.results.some((x) => x.category === c && x.status !== "NA"));
  const visible = r.results.filter((x) => x.status !== "NA" && (filter === "ALL" ? x.status !== "PASS" : x.status === filter) && (cat === "ALL" || x.category === cat));

  async function save() {
    setBusy(true);
    setMsg("");
    try {
      await api(`/api/user/audits/${r.id}/claim`, { method: "POST" });
      setMsg("Сохранено в личном кабинете");
      onUpdate({ ...r, owned: true });
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) router.push(`/register?claim=${r.id}`);
      else setMsg(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  }

  async function buy(product = "full_audit") {
    setBusy(true);
    setMsg("");
    try {
      const p = await api<{ confirmation_url: string }>("/api/payments/create", { method: "POST", body: { product, audit_id: r.id, receipt_email: receiptEmail } });
      window.location.href = p.confirmation_url;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) router.push(`/register?claim=${r.id}&buy=1`);
      else setMsg(e instanceof Error ? e.message : "Ошибка оплаты");
      setBusy(false);
    }
  }

  return (
    <div className="relative">
      <div aria-hidden className="absolute inset-x-0 top-0 h-[420px] bg-[radial-gradient(ellipse_60%_100%_at_50%_0%,rgba(168,190,255,0.08),transparent)]" />
      <div className="relative mx-auto max-w-6xl px-4 pb-10 pt-10 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <Label>Отчёт об автоматической проверке</Label>
            <h1 className="mt-2 break-all font-mono text-[20px] text-text sm:text-[24px]">{r.url}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-[12.5px] text-dim">
              <span>{dt(r.finished_at || r.created_at)}</span>·<span>{r.facts.site_type_ru}</span>·<span>страниц: {r.facts.pages.length}</span>
              {r.facts.mode === "ecommerce" && <Badge color="var(--warn)">E-COMMERCE</Badge>}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {r.full_access ? (
              <Button asChild variant="secondary"><a href={`/api/report/${r.id}/pdf`}><Download className="size-4" /> Скачать PDF</a></Button>
            ) : null}
            {!r.owned && <Button variant="secondary" onClick={save} disabled={busy}><Save className="size-4" /> Сохранить в кабинет</Button>}
            <Button asChild variant="ghost"><Link href="/"><RotateCw className="size-4" /> Новая проверка</Link></Button>
          </div>
        </div>
        {msg && <div className="mt-3 text-[13px] text-muted">{msg}</div>}

        <div className="mt-8 grid gap-4 lg:grid-cols-[1fr_1.15fr]">
          <div className="panel relative flex flex-col items-center gap-6 overflow-hidden rounded-2xl p-6 text-center sm:flex-row sm:text-left">
            <Spotlight size={380} />
            <ScoreRing score={r.score} />
            <div className="relative">
              <Label>Ваш результат</Label>
              <div className="mt-2 text-[15px] font-medium leading-snug">Russian Website Compliance Score</div>
              <p className="mt-2 text-[12.5px] leading-relaxed text-dim">Score отражает только результаты автоматических проверок сервиса и не является официальной оценкой соответствия законодательству РФ.</p>
            </div>
          </div>
          <ExposureCard exp={r.exposure_full} />
        </div>

        <div className="mt-4">
          <Counters counts={r.counts} onPick={setFilter} active={filter} />
        </div>

        {r.ai?.summary && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="panel mt-4 rounded-2xl p-5">
            <div className="flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.14em] text-dim"><Sparkles className="size-3.5" /> Краткий вывод</div>
            <p className="mt-2 text-[14px] leading-relaxed text-muted">{r.ai.summary}</p>
          </motion.div>
        )}

        {!r.full_access && (
          <div className="panel border-beam relative mt-6 overflow-hidden rounded-2xl p-6 sm:p-7">
            <div className="flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-center">
              <div>
                <div className="text-[17px] font-semibold tracking-tight">Полный аудит{priceOf("full_audit") ? ` — ${rub(priceOf("full_audit")!.amount_rub)}` : ""}</div>
                <p className="mt-1 max-w-xl text-[13.5px] text-muted">Доказательства и тексты норм, AI-объяснения, проверка безопасности (Security Skills), реестры, финансовая экспозиция и полный PDF-отчёт.</p>
              </div>
              <Magnetic>
                <Button variant="primary" size="lg" onClick={() => buy("full_audit")} disabled={busy || !prices?.payments_enabled} className="uppercase">Получить полный аудит <ArrowRight className="size-4" /></Button>
              </Magnetic>
            </div>
          </div>
        )}

        <section className="mt-12">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-[20px] font-semibold tracking-tight">
              {filter === "ALL" ? "Проблемы и пункты для проверки" : filter === "PASS" ? "Пройденные проверки" : filter === "UNKNOWN" ? "Невозможно определить автоматически" : filter === "FAIL" ? "Проблемы" : "Требуют внимания"}
            </h2>
            <div className="flex flex-wrap gap-1.5">
              {["ALL", ...cats].map((c) => (
                <button key={c} onClick={() => setCat(c)} className={cx("rounded-full border px-3 py-1 text-[12px] transition", cat === c ? "border-white/30 bg-white/[0.07] text-text" : "border-line text-dim hover:text-text")}>
                  {c === "ALL" ? "Все категории" : c}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-3">
            {visible.length === 0 ? (
              <div className="panel rounded-2xl p-8 text-center text-[14px] text-muted">В этой выборке пунктов нет.</div>
            ) : (
              visible.map((x, i) => <IssueCard key={x.rule_id} r={x} ai={r.ai?.items?.[x.rule_id]} locked={!r.full_access} defaultOpen={i === 0 && x.status === "FAIL"} />)
            )}
          </div>
          {filter === "ALL" && (
            <div className="mt-8 grid gap-4 md:grid-cols-2">
              <div className="panel rounded-2xl p-5">
                <div className="text-[14px] font-medium">Пройдено проверок: {passed.length}</div>
                <ul className="mt-3 space-y-1.5">
                  {passed.map((p) => <li key={p.rule_id} className="flex gap-2 text-[13px] text-muted"><span className="text-ok">✓</span>{p.title}</li>)}
                </ul>
              </div>
              <div className="panel rounded-2xl p-5">
                <div className="text-[14px] font-medium">Невозможно определить автоматически: {unknown.length}</div>
                <ul className="mt-3 space-y-2">
                  {unknown.map((p) => <li key={p.rule_id} className="text-[13px] text-muted"><span className="text-text">{p.title}.</span> {p.fact}</li>)}
                </ul>
              </div>
            </div>
          )}
          {issues.length === 0 && filter === "ALL" && (
            <p className="mt-4 text-center text-[13px] text-dim">Проблем и пунктов для ручной проверки не найдено среди проверенных страниц.</p>
          )}
        </section>

        {r.comparison && <ComparisonPanel c={r.comparison} />}

        {r.security && <SecurityPanel security={r.security} registries={r.registries ?? null} />}

        {prices && prices.prices.length > 0 && (
          <section className="mt-14">
            <div className="panel noise relative overflow-hidden rounded-3xl p-6 sm:p-8">
              <Spotlight size={600} />
              <div className="relative">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <Label>{r.full_access ? "Полный аудит" : "Экспресс-проверка завершена"}</Label>
                    <h2 className="mt-2 text-[22px] font-semibold tracking-tight">{r.full_access ? "Проверить сайт ещё раз" : "Что можно открыть дополнительно"}</h2>
                  </div>
                  <Button asChild variant="ghost" size="sm"><Link href="/pricing">Все тарифы →</Link></Button>
                </div>
                {prices.payments_enabled && (
                  <div className="mt-5 max-w-sm">
                    <label htmlFor="receipt" className="mb-1.5 block text-[13px] text-muted">Email для кассового чека</label>
                    <input id="receipt" type="email" autoComplete="email" value={receiptEmail} onChange={(e) => setReceiptEmail(e.target.value)} placeholder="name@example.ru"
                      className="h-10 w-full rounded-xl border border-line bg-panel-2/40 px-3 text-[14px] outline-none focus:border-line-2" />
                    <p className="mt-1 text-[11.5px] text-dim">Нужен только чтобы отправить чек. В аккаунте не сохраняется, для входа не используется.</p>
                  </div>
                )}
                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  {prices.prices.filter((p) => p.code === "recheck" || (p.code === "full_audit" && !r.full_access)).map((p) => (
                    <div key={p.code} className={cx("flex flex-col rounded-2xl border p-5", p.code === "full_audit" ? "border-white/25 bg-white/[0.03]" : "border-line bg-panel-2/40")}>
                      <div className="text-[14px] font-medium">{p.title}</div>
                      <div className="mt-2 text-[26px] font-semibold tabular-nums">{rub(p.amount_rub)}</div>
                      <p className="mt-2 flex-1 text-[12.5px] leading-relaxed text-muted">{p.description}</p>
                      <Button variant={p.code === "full_audit" ? "primary" : "secondary"} className="mt-4 w-full" disabled={busy || (prices.payments_enabled && !receiptEmail.includes("@")) || (!prices.payments_enabled && !r.full_access)}
                        onClick={() => buy(p.code)}>
                        {prices.payments_enabled ? "Оформить" : "Сейчас бесплатно"}
                      </Button>
                    </div>
                  ))}
                </div>
                {!prices.payments_enabled && <p className="mt-4 text-[12px] text-dim">Приём оплаты ещё не подключён — сейчас полный аудит открыт бесплатно. Цены показаны для ознакомления и настраиваются в админке.</p>}
              </div>
            </div>
          </section>
        )}

        <section className="mt-14">
          <h2 className="mb-4 text-[20px] font-semibold tracking-tight">Что найдено на сайте</h2>
          <FactsPanels f={r.facts} full={r.full_access} />
        </section>

        <section className="mt-12 rounded-2xl border border-line p-5 text-[12px] leading-relaxed text-dim">
          <p>{DISCLAIMER}</p>
          <p className="mt-2">Применены правила: {r.snapshot?.rules?.map((x) => `${x.rule_id} v${x.version}`).join(", ")}. Редакции норм сверены с официальным источником. Подробнее — <Link href="/methodology" className="underline underline-offset-2">методика</Link>.</p>
          {r.exposure_full.items.length > 0 && <p className="mt-2">Финансовая экспозиция: {rub(r.exposure_full.min)} – {rub(r.exposure_full.max)} — не является прогнозом штрафа.</p>}
        </section>
      </div>
    </div>
  );
}

const STATUS_RU: Record<string, string> = { FAIL: "Проблема", REVIEW: "Требует внимания", PASS: "Пройдено", UNKNOWN: "Не определено", NA: "Не применимо" };

function ComparisonPanel({ c }: { c: Comparison }) {
  const delta = (a: number | null, b: number | null) => (a === null || b === null ? "—" : `${a} → ${b}${b - a !== 0 ? ` (${b - a > 0 ? "+" : ""}${b - a})` : ""}`);
  return (
    <section className="mt-14">
      <h2 className="mb-4 text-[20px] font-semibold tracking-tight">Сравнение с предыдущей проверкой</h2>
      <div className="panel rounded-2xl p-6">
        <div className="grid gap-3 sm:grid-cols-4">
          <Cmp label="Score" value={delta(c.score_before, c.score_after)} />
          <Cmp label="Security score" value={delta(c.security_before, c.security_after)} />
          <Cmp label="Исправлено" value={String(c.resolved)} color="var(--ok)" />
          <Cmp label="Новых проблем" value={String(c.new_issues)} color={c.new_issues ? "var(--risk)" : undefined} />
        </div>
        <div className="mt-3 text-[12.5px] text-dim">Не исправлено: {c.unchanged_issues}. <Link href={`/audit/${c.previous_id}`} className="underline underline-offset-2">Открыть предыдущий отчёт</Link></div>
        {c.changes.length > 0 && (
          <ul className="mt-4 space-y-1.5 text-[13px]">
            {c.changes.map((x) => (
              <li key={x.rule_id} className="flex flex-wrap items-center gap-2 text-muted">
                <span className="text-text">{x.title}</span>
                <span className="text-dim">{STATUS_RU[x.was] ?? x.was} → {STATUS_RU[x.now] ?? x.now}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function Cmp({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-xl border border-line bg-panel-2/40 p-4">
      <div className="text-[11.5px] uppercase tracking-[0.12em] text-dim">{label}</div>
      <div className="mt-1 text-[20px] font-semibold tabular-nums" style={color ? { color } : undefined}>{value}</div>
    </div>
  );
}
