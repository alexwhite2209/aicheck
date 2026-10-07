"use client";

import * as Tabs from "@radix-ui/react-tabs";
import { CheckCircle2, ExternalLink, FlaskConical, Plus, RefreshCw, Rocket, XCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { api, ApiError } from "@/lib/api";
import { d, dt, rub } from "@/lib/format";
import { Badge, Button, Dialog, DialogContent, DialogTrigger, Input, Label, cx } from "./ui";

type Dash = { audits_total: number; audits_24h: number; audits_running: number; audits_failed: number; users: number; revenue_rub: number; avg_score: number | null; avg_exposure_min: number | null; crawler_errors: { id: string; url: string; error: string; created_at: string; detail: string | null }[] };
type Version = { id: string; version: number; status: string; severity: string; mode: string; basis: string[]; basis_articles: string[]; finance: { group: string; kind: string } | null; why: string; fix: string; effective_from: string; effective_to: string | null; notes: string; test_report: { passed?: boolean; cases?: { name: string; expected: string; got: string; ok: boolean }[] } | null; created_by: string; published_by: string | null };
type RuleT = { id: string; title: string; category: string; enabled: boolean; implemented: boolean; versions: Version[] };
type Act = { id: string; title: string; short: string; edition: string; checked_at: string; official_url: string };
type Art = { id: string; key: string; act_id: string; article: string; part: string; paragraph: string; title: string; text: string; edition: string; effective_from: string | null; effective_to: string | null; checked_at: string; official_url: string; status: string };

const TABS = [["dash", "Dashboard"], ["audits", "Аудиты"], ["users", "Пользователи"], ["rules", "Rules"], ["norms", "Нормативная база"], ["ai", "AI"], ["prices", "Цены"], ["log", "Журнал"]] as const;
const VSTATUS: Record<string, string> = { draft: "var(--unk)", tested: "var(--warn)", published: "var(--ok)", retired: "var(--dim)" };

export function AdminView() {
  const [ok, setOk] = React.useState(false);
  const router = useRouter();
  React.useEffect(() => {
    api<{ user: { role: string } }>("/api/auth/me").then((m) => (m.user.role === "admin" ? setOk(true) : router.replace("/account"))).catch(() => router.replace("/login"));
  }, [router]);
  if (!ok) return <div className="min-h-[60vh]" />;
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <Label>Администрирование</Label>
      <h1 className="mt-2 text-[28px] font-semibold tracking-tight">Админ-панель</h1>
      <Tabs.Root defaultValue="dash" className="mt-6">
        <Tabs.List className="no-scrollbar flex gap-1 overflow-x-auto border-b border-line pb-px">
          {TABS.map(([v, l]) => (
            <Tabs.Trigger key={v} value={v} className="relative whitespace-nowrap px-3.5 py-2.5 text-[13.5px] text-dim transition hover:text-text data-[state=active]:text-text data-[state=active]:after:absolute data-[state=active]:after:inset-x-2 data-[state=active]:after:-bottom-px data-[state=active]:after:h-px data-[state=active]:after:bg-white">{l}</Tabs.Trigger>
          ))}
        </Tabs.List>
        <Tabs.Content value="dash" className="mt-6"><DashTab /></Tabs.Content>
        <Tabs.Content value="audits" className="mt-6"><AuditsTab /></Tabs.Content>
        <Tabs.Content value="users" className="mt-6"><UsersTab /></Tabs.Content>
        <Tabs.Content value="rules" className="mt-6"><RulesTab /></Tabs.Content>
        <Tabs.Content value="norms" className="mt-6"><NormsTab /></Tabs.Content>
        <Tabs.Content value="ai" className="mt-6"><AITab /></Tabs.Content>
        <Tabs.Content value="prices" className="mt-6"><PricesTab /></Tabs.Content>
        <Tabs.Content value="log" className="mt-6"><LogTab /></Tabs.Content>
      </Tabs.Root>
    </div>
  );
}

function useLoad<T>(path: string) {
  const [data, setData] = React.useState<T | null>(null);
  const [err, setErr] = React.useState("");
  const reload = React.useCallback(() => {
    api<T>(path).then(setData).catch((e) => setErr(e instanceof ApiError ? e.message : "Ошибка"));
  }, [path]);
  React.useEffect(() => { reload(); }, [reload]);
  return { data, err, reload };
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="panel rounded-2xl p-4">
      <div className="text-[11.5px] uppercase tracking-[0.12em] text-dim">{label}</div>
      <div className="mt-1.5 text-[24px] font-semibold tabular-nums tracking-tight">{value}</div>
    </div>
  );
}

function DashTab() {
  const { data } = useLoad<Dash>("/api/admin/dashboard");
  if (!data) return null;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Аудитов всего" value={data.audits_total} />
        <Stat label="За 24 часа" value={data.audits_24h} />
        <Stat label="Пользователи" value={data.users} />
        <Stat label="Выручка" value={rub(data.revenue_rub)} />
        <Stat label="Средний Score" value={data.avg_score ?? "—"} />
        <Stat label="Средняя экспозиция" value={data.avg_exposure_min !== null ? rub(data.avg_exposure_min) : "—"} />
        <Stat label="В работе" value={data.audits_running} />
        <Stat label="Ошибки crawler" value={data.audits_failed} />
      </div>
      <div className="panel rounded-2xl p-5">
        <div className="mb-3 text-[14px] font-medium">Последние ошибки crawler</div>
        {data.crawler_errors.length === 0 ? <div className="text-[13px] text-dim">Ошибок нет.</div> : (
          <ul className="space-y-2 text-[13px]">
            {data.crawler_errors.map((e) => (
              <li key={e.id} className="flex flex-wrap justify-between gap-2 border-b border-line pb-2 last:border-0">
                <span className="font-mono text-text">{e.url}</span>
                <span className="text-muted">{e.error} <span className="text-dim">{e.detail ? `(${e.detail.slice(0, 90)})` : ""} · {dt(e.created_at)}</span></span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function AuditsTab() {
  const [q, setQ] = React.useState("");
  const { data, reload } = useLoad<{ audits: { id: string; url: string; user: string | null; created_at: string; score: number | null; exposure_min: number | null; exposure_max: number | null; status: string; error: string | null; site_type: string | null }[] }>(`/api/admin/audits${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  return (
    <div className="space-y-4">
      <div className="flex max-w-md gap-2"><Input placeholder="Поиск по URL" value={q} onChange={(e) => setQ(e.target.value)} /><Button onClick={reload}><RefreshCw className="size-4" /></Button></div>
      <div className="panel overflow-x-auto rounded-2xl">
        <table className="w-full min-w-[820px] text-left text-[12.5px]">
          <thead className="text-dim"><tr>{["URL", "Пользователь", "Дата", "Score", "Exposure", "Тип", "Статус", ""].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>{data?.audits.map((a) => (
            <tr key={a.id} className="border-t border-line text-muted">
              <td className="max-w-[260px] truncate p-3 font-mono text-text">{a.url}</td><td className="p-3">{a.user || "аноним"}</td><td className="p-3">{dt(a.created_at)}</td>
              <td className="p-3 tabular-nums">{a.score ?? "—"}</td><td className="p-3 tabular-nums">{a.exposure_min ? `${rub(a.exposure_min)}–${rub(a.exposure_max)}` : "—"}</td>
              <td className="p-3">{a.site_type || "—"}</td>
              <td className="p-3"><Badge color={a.status === "done" ? "var(--ok)" : a.status === "failed" ? "var(--risk)" : "var(--warn)"}>{a.status}</Badge></td>
              <td className="p-3"><Link href={`/audit/${a.id}`} className="text-text"><ExternalLink className="size-3.5" /></Link></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

type AdminUser = { id: string; login: string; role: string; created_at: string; audits: number; unlimited: boolean; pro: boolean; is_active: boolean };

function UsersTab() {
  const { data, reload } = useLoad<{ users: AdminUser[] }>("/api/admin/users");
  const [msg, setMsg] = React.useState("");
  async function patch(id: string, body: Record<string, unknown>) {
    setMsg("");
    try {
      await api(`/api/admin/users/${id}`, { method: "PUT", body });
      reload();
      return true;
    } catch (e) { setMsg(e instanceof Error ? e.message : "Ошибка"); return false; }
  }
  return (
    <div className="space-y-3">
      <p className="max-w-3xl text-[13px] text-muted">Безлимит — полный отчёт и проверка безопасности бесплатно и без ограничений по частоте. Роль «админ» даёт доступ к этой панели. Администраторам всё доступно бесплатно по умолчанию.</p>
      {msg && <div className="text-[13px] text-risk">{msg}</div>}
      <div className="panel overflow-x-auto rounded-2xl">
        <table className="w-full min-w-[760px] text-left text-[13px]">
          <thead className="text-dim"><tr>{["Логин", "Роль", "Доступ", "Проверок", "Регистрация", "Управление"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>{data?.users.map((u) => (
            <tr key={u.id} className="border-t border-line text-muted">
              <td className="p-3 text-text">{u.login}{!u.is_active && <span className="ml-2 text-risk">(заблокирован)</span>}</td>
              <td className="p-3">{u.role === "admin" ? <Badge color="var(--ok)">админ</Badge> : "пользователь"}</td>
              <td className="p-3">{u.pro ? <Badge color="var(--ok)">безлимит</Badge> : "обычный"}</td>
              <td className="p-3 tabular-nums">{u.audits}</td>
              <td className="p-3">{d(u.created_at)}</td>
              <td className="p-3">
                <div className="flex flex-wrap gap-1.5">
                  {u.role !== "admin" && (
                    <Button size="sm" variant={u.unlimited ? "secondary" : "primary"} onClick={() => patch(u.id, { unlimited: !u.unlimited })}>
                      {u.unlimited ? "Снять безлимит" : "Выдать безлимит"}
                    </Button>
                  )}
                  <Button size="sm" variant="secondary" onClick={() => patch(u.id, { role: u.role === "admin" ? "user" : "admin" })}>
                    {u.role === "admin" ? "Снять админа" : "Сделать админом"}
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => {
                    const password = window.prompt(`Новый пароль для «${u.login}» (не менее 8 символов)`);
                    if (password) patch(u.id, { password }).then((ok) => ok && setMsg(`Пароль для «${u.login}» изменён`));
                  }}>
                    Новый пароль
                  </Button>
                </div>
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

function RulesTab() {
  const { data, reload } = useLoad<{ rules: RuleT[]; unseeded_implementations: string[] }>("/api/admin/rules");
  const [msg, setMsg] = React.useState("");
  async function act(path: string, body?: unknown, method = "POST") {
    setMsg("");
    try {
      await api(path, { method, body });
      reload();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Ошибка"); }
  }
  if (!data) return null;
  return (
    <div className="space-y-3">
      <p className="max-w-3xl text-[13px] text-muted">Изменение правила — только через новую версию: черновик → тестирование (unit-тесты правила) → публикация. Старые версии не перезаписываются; аудиты хранят версию, применённую в момент проверки. AI не может менять правила.</p>
      {msg && <div className="text-[13px] text-risk">{msg}</div>}
      {data.rules.map((r) => {
        const cur = r.versions.find((v) => v.status === "published") || r.versions[0];
        return (
          <div key={r.id} className="panel rounded-2xl p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[12.5px] text-dim">{r.id}</span>
                  <Badge color={r.enabled ? "var(--ok)" : "var(--unk)"}>{r.enabled ? "включено" : "выключено"}</Badge>
                  <span className="text-[12px] text-dim">{r.category}</span>
                </div>
                <div className="mt-1 text-[14.5px] font-medium">{r.title}</div>
                {cur && <div className="mt-1 text-[12px] text-dim">v{cur.version} · {cur.severity} · основание: {cur.basis.join(", ")} · с {cur.effective_from}{cur.effective_to ? ` по ${cur.effective_to}` : ""}</div>}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" onClick={() => act(`/api/admin/rules/${r.id}`, { enabled: !r.enabled }, "PUT")}>{r.enabled ? "Выключить" : "Включить"}</Button>
                {cur && <NewVersionDialog rule={r} base={cur} onDone={reload} />}
              </div>
            </div>
            <div className="mt-3 space-y-1.5">
              {r.versions.map((v) => (
                <div key={v.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-line bg-panel-2/40 px-3 py-2 text-[12.5px]">
                  <span className="font-mono">v{v.version}</span>
                  <Badge color={VSTATUS[v.status]}>{v.status}</Badge>
                  <span className="text-dim">с {v.effective_from}{v.effective_to ? ` по ${v.effective_to}` : ""} · {v.created_by}</span>
                  {v.test_report?.passed !== undefined && (
                    <span className={cx("inline-flex items-center gap-1", v.test_report.passed ? "text-ok" : "text-risk")}>
                      {v.test_report.passed ? <CheckCircle2 className="size-3.5" /> : <XCircle className="size-3.5" />} тесты {v.test_report.cases?.filter((c) => c.ok).length}/{v.test_report.cases?.length}
                    </span>
                  )}
                  <span className="ml-auto flex gap-1.5">
                    {(v.status === "draft" || v.status === "tested") && <Button size="sm" variant="ghost" onClick={() => act(`/api/admin/rules/${r.id}/versions/${v.id}/test`)}><FlaskConical className="size-3.5" /> Тест</Button>}
                    {v.status === "tested" && <Button size="sm" variant="primary" onClick={() => act(`/api/admin/rules/${r.id}/versions/${v.id}/publish`)}><Rocket className="size-3.5" /> Опубликовать</Button>}
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function NewVersionDialog({ rule, base, onDone }: { rule: RuleT; base: Version; onDone: () => void }) {
  const [f, setF] = React.useState({ severity: base.severity, basis: base.basis.join(", "), group: base.finance?.group || "", kind: base.finance?.kind || "estimated", why: base.why, fix: base.fix, effective_from: new Date().toISOString().slice(0, 10), notes: "" });
  const [err, setErr] = React.useState("");
  const [open, setOpen] = React.useState(false);
  async function save() {
    setErr("");
    try {
      await api(`/api/admin/rules/${rule.id}/versions`, { method: "POST", body: {
        severity: f.severity, basis: f.basis.split(",").map((s) => s.trim()).filter(Boolean), finance: f.group ? { group: f.group, kind: f.kind } : null,
        why: f.why, fix: f.fix, effective_from: f.effective_from, notes: f.notes } });
      setOpen(false);
      onDone();
    } catch (e) { setErr(e instanceof Error ? e.message : "Ошибка"); }
  }
  const field = "w-full rounded-xl border border-line-2 bg-panel px-3 py-2 text-[13px] text-text outline-none focus:border-line-3";
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm" variant="secondary"><Plus className="size-3.5" /> Новая версия</Button></DialogTrigger>
      <DialogContent title={`Новая версия ${rule.id}`} wide>
        <div className="grid gap-3 text-[13px]">
          <label className="grid gap-1"><span className="text-dim">Критичность</span>
            <select className={field} value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })}>{["critical", "high", "medium", "low", "info"].map((s) => <option key={s}>{s}</option>)}</select></label>
          <label className="grid gap-1"><span className="text-dim">Нормы (ключи из нормативной базы, через запятую)</span><input className={field} value={f.basis} onChange={(e) => setF({ ...f, basis: e.target.value })} /></label>
          <div className="grid grid-cols-2 gap-3">
            <label className="grid gap-1"><span className="text-dim">Группа санкции (КоАП)</span><input className={field} value={f.group} onChange={(e) => setF({ ...f, group: e.target.value })} placeholder="KOAP:13.11:3:" /></label>
            <label className="grid gap-1"><span className="text-dim">Тип оценки</span><select className={field} value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}><option value="direct">direct</option><option value="estimated">estimated</option></select></label>
          </div>
          <label className="grid gap-1"><span className="text-dim">Почему это важно</span><textarea rows={3} className={field} value={f.why} onChange={(e) => setF({ ...f, why: e.target.value })} /></label>
          <label className="grid gap-1"><span className="text-dim">Что сделать</span><textarea rows={3} className={field} value={f.fix} onChange={(e) => setF({ ...f, fix: e.target.value })} /></label>
          <div className="grid grid-cols-2 gap-3">
            <label className="grid gap-1"><span className="text-dim">Действует с</span><input type="date" className={field} value={f.effective_from} onChange={(e) => setF({ ...f, effective_from: e.target.value })} /></label>
            <label className="grid gap-1"><span className="text-dim">Комментарий (какая редакция нормы)</span><input className={field} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></label>
          </div>
          {err && <div className="text-risk">{err}</div>}
          <div className="flex justify-end"><Button variant="primary" onClick={save}>Создать черновик</Button></div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function NormsTab() {
  const { data, reload } = useLoad<{ acts: Act[]; articles: Art[] }>("/api/admin/normative-acts");
  const [open, setOpen] = React.useState<string | null>(null);
  if (!data) return null;
  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-2">
        {data.acts.map((a) => (
          <div key={a.id} className="panel rounded-2xl p-4">
            <div className="font-mono text-[12px] text-dim">{a.id}</div>
            <div className="mt-1 text-[14px] font-medium">{a.title}</div>
            <div className="mt-1 text-[12.5px] text-muted">{a.edition} · сверено {a.checked_at}</div>
            <a href={a.official_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-[12.5px] text-text underline decoration-line-3 underline-offset-4">Официальный источник <ExternalLink className="size-3" /></a>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between">
        <div className="text-[14px] font-medium">Нормы ({data.articles.length})</div>
        <NewArticleDialog acts={data.acts} onDone={reload} />
      </div>
      <div className="space-y-2">
        {data.articles.map((x) => (
          <div key={x.id} className="panel rounded-xl p-3">
            <button className="flex w-full flex-wrap items-center gap-2 text-left text-[13px]" onClick={() => setOpen(open === x.id ? null : x.id)}>
              <span className="font-mono text-[12px] text-dim">{x.key}</span>
              <span className="text-text">{x.title}</span>
              <Badge color={x.status === "active" ? "var(--ok)" : "var(--unk)"}>{x.status}</Badge>
              <span className="ml-auto text-[12px] text-dim">{x.effective_from ? `с ${x.effective_from}` : "в силе на дату сверки"} · сверено {x.checked_at}</span>
            </button>
            {open === x.id && <pre className="mt-3 whitespace-pre-wrap rounded-lg border border-line bg-black/30 p-3 font-mono text-[12px] leading-relaxed text-muted">{x.text}</pre>}
          </div>
        ))}
      </div>
    </div>
  );
}

function NewArticleDialog({ acts, onDone }: { acts: Act[]; onDone: () => void }) {
  const today = new Date().toISOString().slice(0, 10);
  const [f, setF] = React.useState({ key: "", act_id: acts[0]?.id || "", article: "", part: "", paragraph: "", title: "", text: "", edition: "", effective_from: "", official_url: "http://pravo.gov.ru/", checked_at: today });
  const [err, setErr] = React.useState("");
  const [open, setOpen] = React.useState(false);
  const field = "w-full rounded-xl border border-line-2 bg-panel px-3 py-2 text-[13px] text-text outline-none focus:border-line-3";
  async function save() {
    setErr("");
    try {
      await api("/api/admin/normative-articles", { method: "POST", body: { ...f, effective_from: f.effective_from || null } });
      setOpen(false);
      onDone();
    } catch (e) { setErr(e instanceof Error ? e.message : "Ошибка"); }
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm" variant="secondary"><Plus className="size-3.5" /> Новая редакция нормы</Button></DialogTrigger>
      <DialogContent title="Новая редакция нормы" wide>
        <div className="grid gap-3 text-[13px]">
          <p className="text-dim">Текст — дословно из официального источника (pravo.gov.ru или сайт госоргана). Прежняя редакция сохранится как замещённая.</p>
          <div className="grid grid-cols-2 gap-3">
            <label className="grid gap-1"><span className="text-dim">Ключ нормы</span><input className={field} placeholder="152-FZ:18.1:2:" value={f.key} onChange={(e) => setF({ ...f, key: e.target.value })} /></label>
            <label className="grid gap-1"><span className="text-dim">Акт</span><select className={field} value={f.act_id} onChange={(e) => setF({ ...f, act_id: e.target.value })}>{acts.map((a) => <option key={a.id} value={a.id}>{a.short}</option>)}</select></label>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {(["article", "part", "paragraph"] as const).map((k) => <label key={k} className="grid gap-1"><span className="text-dim">{{ article: "Статья", part: "Часть", paragraph: "Пункт" }[k]}</span><input className={field} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>)}
          </div>
          <label className="grid gap-1"><span className="text-dim">Название требования</span><input className={field} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></label>
          <label className="grid gap-1"><span className="text-dim">Текст нормы</span><textarea rows={6} className={field} value={f.text} onChange={(e) => setF({ ...f, text: e.target.value })} /></label>
          <div className="grid grid-cols-2 gap-3">
            <label className="grid gap-1"><span className="text-dim">Редакция</span><input className={field} value={f.edition} onChange={(e) => setF({ ...f, edition: e.target.value })} placeholder="ред. от … № …-ФЗ" /></label>
            <label className="grid gap-1"><span className="text-dim">Вступает в силу</span><input type="date" className={field} value={f.effective_from} onChange={(e) => setF({ ...f, effective_from: e.target.value })} /></label>
          </div>
          <label className="grid gap-1"><span className="text-dim">Официальный источник (URL)</span><input className={field} value={f.official_url} onChange={(e) => setF({ ...f, official_url: e.target.value })} /></label>
          {err && <div className="text-risk">{err}</div>}
          <div className="flex justify-end"><Button variant="primary" onClick={save}>Сохранить</Button></div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

type AISet = { provider: string; key_configured: boolean; model: string; temperature: number; max_tokens: number; enabled: boolean };

function AITab() {
  const { data, reload } = useLoad<AISet>("/api/admin/ai/settings");
  if (!data) return null;
  return <AIForm data={data} reload={reload} />;
}

function AIForm({ data, reload }: { data: AISet; reload: () => void }) {
  const [models, setModels] = React.useState<{ id: string; name: string; prompt_price: string; completion_price: string }[]>([]);
  const [f, setF] = React.useState({ model: data.model, temperature: data.temperature, max_tokens: data.max_tokens, enabled: data.enabled });
  const [msg, setMsg] = React.useState("");
  const [filter, setFilter] = React.useState("");
  React.useEffect(() => { api<{ models: typeof models }>("/api/admin/ai/models").then((r) => setModels(r.models)).catch(() => {}); }, []);
  const list = models.filter((m) => !filter || m.id.toLowerCase().includes(filter.toLowerCase())).slice(0, 200);
  async function save() {
    try {
      await api("/api/admin/ai/settings", { method: "PUT", body: f });
      setMsg("Сохранено");
      reload();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Ошибка"); }
  }
  return (
    <div className="panel max-w-2xl space-y-4 rounded-2xl p-6 text-[13.5px]">
      <div>Provider: <span className="text-text">OpenRouter</span> · API-ключ: {data.key_configured ? <span className="text-ok">задан в .env</span> : <span className="text-warn">не задан — отчёты формируются по шаблонам правил</span>}</div>
      <label className="grid gap-1"><span className="text-dim">Модель</span>
        <Input placeholder="фильтр моделей" value={filter} onChange={(e) => setFilter(e.target.value)} />
        <select className="h-11 rounded-xl border border-line-2 bg-panel px-3 text-text" value={f.model} onChange={(e) => setF({ ...f, model: e.target.value })}>
          {!list.find((m) => m.id === f.model) && <option value={f.model}>{f.model}</option>}
          {list.map((m) => <option key={m.id} value={m.id}>{m.id}{m.prompt_price === "0" ? " · бесплатно" : ""}</option>)}
        </select>
        <span className="text-[12px] text-dim">{models.length ? `Доступно моделей: ${models.length}` : "Список моделей не загружен — можно ввести id вручную"}</span>
        <Input value={f.model} onChange={(e) => setF({ ...f, model: e.target.value })} />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="grid gap-1"><span className="text-dim">Temperature</span><Input type="number" step="0.1" min={0} max={1.5} value={f.temperature} onChange={(e) => setF({ ...f, temperature: Number(e.target.value) })} /></label>
        <label className="grid gap-1"><span className="text-dim">Max tokens</span><Input type="number" min={200} max={16000} value={f.max_tokens} onChange={(e) => setF({ ...f, max_tokens: Number(e.target.value) })} /></label>
      </div>
      <label className="flex items-center gap-2"><input type="checkbox" className="accent-white" checked={f.enabled} onChange={(e) => setF({ ...f, enabled: e.target.checked })} /> AI-объяснения включены</label>
      <div className="flex items-center gap-3"><Button variant="primary" onClick={save}>Сохранить</Button>{msg && <span className="text-dim">{msg}</span>}</div>
    </div>
  );
}

function PricesTab() {
  const { data, reload } = useLoad<{ prices: { code: string; title: string; description: string; amount_rub: number; active: boolean; sort: number }[] }>("/api/admin/prices");
  const [msg, setMsg] = React.useState("");
  if (!data) return null;
  return (
    <div className="space-y-3">
      <p className="text-[13px] text-muted">Цены хранятся в базе и отдаются фронтенду через API — в коде страниц их нет.</p>
      {data.prices.map((p) => <PriceRow key={p.code} p={p} onSaved={() => { setMsg("Сохранено"); reload(); }} />)}
      {msg && <div className="text-[13px] text-dim">{msg}</div>}
    </div>
  );
}

function PriceRow({ p, onSaved }: { p: { code: string; title: string; description: string; amount_rub: number; active: boolean; sort: number }; onSaved: () => void }) {
  const [v, setV] = React.useState(p);
  return (
    <div className="panel grid items-end gap-3 rounded-xl p-4 md:grid-cols-[1fr_2fr_120px_auto_auto]">
      <label className="grid gap-1 text-[12px] text-dim">Название<Input value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} /></label>
      <label className="grid gap-1 text-[12px] text-dim">Описание<Input value={v.description} onChange={(e) => setV({ ...v, description: e.target.value })} /></label>
      <label className="grid gap-1 text-[12px] text-dim">Цена, ₽<Input type="number" value={v.amount_rub} onChange={(e) => setV({ ...v, amount_rub: Number(e.target.value) })} /></label>
      <label className="flex h-11 items-center gap-2 text-[13px] text-muted"><input type="checkbox" className="accent-white" checked={v.active} onChange={(e) => setV({ ...v, active: e.target.checked })} /> активен</label>
      <Button variant="secondary" onClick={() => api("/api/admin/prices", { method: "PUT", body: v }).then(onSaved)}>Сохранить</Button>
    </div>
  );
}

function LogTab() {
  const { data } = useLoad<{ log: { at: string; actor: string; action: string; target: string; meta: Record<string, unknown> }[] }>("/api/admin/log");
  return (
    <div className="panel overflow-x-auto rounded-2xl">
      <table className="w-full min-w-[720px] text-left text-[12.5px]">
        <thead className="text-dim"><tr>{["Время", "Кто", "Действие", "Объект", "Детали"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
        <tbody>{data?.log.map((l, i) => (
          <tr key={i} className="border-t border-line text-muted"><td className="p-3">{dt(l.at)}</td><td className="p-3">{l.actor}</td><td className="p-3 font-mono">{l.action}</td><td className="max-w-[240px] truncate p-3">{l.target}</td><td className="max-w-[260px] truncate p-3 font-mono text-[11.5px]">{JSON.stringify(l.meta)}</td></tr>
        ))}</tbody>
      </table>
    </div>
  );
}
