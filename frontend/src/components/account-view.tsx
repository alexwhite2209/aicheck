"use client";

import * as Tabs from "@radix-ui/react-tabs";
import { ArrowDownRight, ArrowUpRight, Download, ExternalLink, LogOut, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { api, ApiError } from "@/lib/api";
import { d, rub } from "@/lib/format";
import { Badge, Button, Dialog, DialogContent, DialogTrigger, Input, Label, cx } from "./ui";

type Row = { id: string; url: string; host: string; status: string; score: number | null; exposure_min: number | null; exposure_max: number | null; created_at: string; paid_full: boolean; counts: { fail: number; review: number } | null };
type SiteT = { id: string; url: string; host: string; monitoring: string; verified?: boolean; audits: Row[] };
type Pay = { id: string; product: string; amount_rub: number; status: string; audit_id: string | null; created_at: string };
type Me = { login: string; role: string; created_at: string; marketing_consent: boolean };

const TABS = [["sites", "Мои сайты"], ["audits", "Проверки"], ["history", "История"], ["pdf", "PDF"], ["monitoring", "Мониторинг"], ["payments", "Платежи"], ["profile", "Профиль"]] as const;

export function AccountView() {
  const [me, setMe] = React.useState<Me | null>(null);
  const [sites, setSites] = React.useState<SiteT[]>([]);
  const [audits, setAudits] = React.useState<Row[]>([]);
  const [payments, setPayments] = React.useState<Pay[]>([]);
  const [newSite, setNewSite] = React.useState("");
  const [msg, setMsg] = React.useState("");
  const router = useRouter();

  const load = React.useCallback(
    () =>
      api<{ user: Me }>("/api/auth/me")
        .then((m) => {
          setMe(m.user);
          return Promise.all([api<{ sites: SiteT[] }>("/api/user/sites"), api<{ audits: Row[] }>("/api/user/audits"), api<{ payments: Pay[] }>("/api/user/payments")]);
        })
        .then(([s, a, p]) => {
          setSites(s.sites);
          setAudits(a.audits);
          setPayments(p.payments);
        })
        .catch((e) => {
          if (e instanceof ApiError && e.status === 401) router.replace("/login");
        }),
    [router],
  );
  React.useEffect(() => { load(); }, [load]);

  async function addSite(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/api/user/sites", { method: "POST", body: { url: newSite } });
      setNewSite("");
      load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Ошибка"); }
  }
  async function runAudit(url: string) {
    try {
      const r = await api<{ id: string }>("/api/audit", { method: "POST", body: { url } });
      router.push(`/audit/${r.id}`);
    } catch (e) { setMsg(e instanceof Error ? e.message : "Ошибка"); }
  }
  async function setMonitoring(id: string, monitoring: string) {
    await api(`/api/user/sites/${id}`, { method: "PUT", body: { monitoring } });
    load();
  }
  async function removeSite(id: string) {
    if (!confirm("Удалить сайт из списка? Проверки сохранятся.")) return;
    await api(`/api/user/sites/${id}`, { method: "DELETE" });
    load();
  }
  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    router.push("/");
    router.refresh();
  }
  async function exportData() {
    const data = await api("/api/user/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "norma-my-data.json";
    a.click();
  }
  async function deleteAccount() {
    if (!confirm("Удалить аккаунт и все проверки без возможности восстановления?")) return;
    await api("/api/user", { method: "DELETE" });
    router.push("/");
    router.refresh();
  }

  if (!me) return <div className="min-h-[60vh]" />;
  const done = audits.filter((a) => a.status === "done");
  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Label>Личный кабинет</Label>
          <h1 className="mt-2 text-[28px] font-semibold tracking-tight">{me.login}</h1>
        </div>
        <Button variant="ghost" onClick={logout}><LogOut className="size-4" /> Выйти</Button>
      </div>
      {msg && <div className="mt-3 text-[13px] text-risk">{msg}</div>}
      <Tabs.Root defaultValue="sites" className="mt-8">
        <Tabs.List className="no-scrollbar flex gap-1 overflow-x-auto border-b border-line pb-px">
          {TABS.map(([v, l]) => (
            <Tabs.Trigger key={v} value={v} className="relative whitespace-nowrap px-3.5 py-2.5 text-[13.5px] text-dim transition hover:text-text data-[state=active]:text-text data-[state=active]:after:absolute data-[state=active]:after:inset-x-2 data-[state=active]:after:-bottom-px data-[state=active]:after:h-px data-[state=active]:after:bg-white">
              {l}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        <Tabs.Content value="sites" className="mt-6 space-y-4">
          <form onSubmit={addSite} className="flex max-w-xl gap-2">
            <Input placeholder="example.ru" value={newSite} onChange={(e) => setNewSite(e.target.value)} />
            <Button type="submit" variant="secondary"><Plus className="size-4" /> Добавить</Button>
          </form>
          {sites.length === 0 && <Empty text="Сайтов пока нет. Добавьте адрес или сохраните проверку со страницы отчёта." />}
          {sites.map((s) => {
            const [last, prev] = s.audits;
            return (
              <div key={s.id} className="panel rounded-2xl p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-mono text-[16px]">{s.host}</div>
                    <div className="text-[12.5px] text-dim">Проверок: {s.audits.length}</div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                                        <Button variant="primary" size="sm" onClick={() => runAudit(s.url)}>Проверить снова</Button>
                    <Button variant="ghost" size="sm" onClick={() => removeSite(s.id)} aria-label="Удалить"><Trash2 className="size-4" /></Button>
                  </div>
                </div>
                {last && (
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <Metric label="Score" value={last.score === null ? "—" : `${last.score} / 100`} />
                    <Metric label="Экспозиция" value={last.exposure_min ? `${rub(last.exposure_min)} – ${rub(last.exposure_max)}` : "0 ₽"} />
                    {prev ? <Compare prev={prev} last={last} /> : <Metric label="Сравнение" value="после второй проверки" dim />}
                  </div>
                )}
              </div>
            );
          })}
        </Tabs.Content>

        <Tabs.Content value="audits" className="mt-6"><AuditTable rows={audits} /></Tabs.Content>

        <Tabs.Content value="history" className="mt-6 space-y-3">
          {done.length === 0 && <Empty text="Завершённых проверок пока нет." />}
          {done.map((a) => (
            <Link key={a.id} href={`/audit/${a.id}`} className="panel flex items-center justify-between gap-4 rounded-2xl p-4 transition hover:border-line-2">
              <div>
                <div className="font-mono text-[14px]">{a.host}</div>
                <div className="text-[12px] text-dim">{d(a.created_at)}</div>
              </div>
              <div className="text-right">
                <div className="text-[18px] font-semibold tabular-nums">{a.score ?? "—"} <span className="text-[13px] text-dim">/ 100</span></div>
                <div className="text-[12.5px] text-muted tabular-nums">{a.exposure_min ? rub(a.exposure_min) : "0 ₽"}</div>
              </div>
            </Link>
          ))}
        </Tabs.Content>

        <Tabs.Content value="pdf" className="mt-6 space-y-2">
          {done.length === 0 && <Empty text="PDF появятся после завершения проверок." />}
          {done.map((a) => (
            <div key={a.id} className="panel flex items-center justify-between gap-3 rounded-xl p-4">
              <div className="font-mono text-[13.5px]">{a.host} · {d(a.created_at)}</div>
              <Button asChild size="sm" variant="secondary"><a href={`/api/report/${a.id}/pdf`}><Download className="size-4" /> PDF</a></Button>
            </div>
          ))}
        </Tabs.Content>

        <Tabs.Content value="monitoring" className="mt-6 space-y-3">
          <p className="max-w-2xl text-[13.5px] text-muted">Выберите частоту автоматических проверок. Когда на сайте появятся новые элементы, которые могут влиять на результат аудита, вы получите уведомление. Функция в разработке — настройка сохраняется уже сейчас.</p>
          {sites.length === 0 && <Empty text="Добавьте сайт, чтобы настроить мониторинг." />}
          {sites.map((s) => (
            <div key={s.id} className="panel flex flex-wrap items-center justify-between gap-3 rounded-xl p-4">
              <div className="font-mono text-[14px]">{s.host}</div>
              <div className="flex gap-1">
                {[["off", "Выключен"], ["daily", "Ежедневно"], ["weekly", "Еженедельно"], ["monthly", "Ежемесячно"]].map(([v, l]) => (
                  <button key={v} onClick={() => setMonitoring(s.id, v)} className={cx("rounded-full border px-3 py-1 text-[12.5px] transition", s.monitoring === v ? "border-white/30 bg-white/[0.08] text-text" : "border-line text-dim hover:text-text")}>{l}</button>
                ))}
              </div>
            </div>
          ))}
        </Tabs.Content>

        <Tabs.Content value="payments" className="mt-6">
          {payments.length === 0 ? <Empty text="Платежей пока нет." /> : (
            <div className="panel overflow-hidden rounded-2xl">
              <table className="w-full text-left text-[13px]">
                <thead className="text-dim"><tr><th className="p-3 font-medium">Дата</th><th className="p-3 font-medium">Услуга</th><th className="p-3 font-medium">Сумма</th><th className="p-3 font-medium">Статус</th></tr></thead>
                <tbody>{payments.map((p) => (
                  <tr key={p.id} className="border-t border-line text-muted"><td className="p-3">{d(p.created_at)}</td><td className="p-3">{p.product}</td><td className="p-3 tabular-nums">{rub(p.amount_rub)}</td>
                    <td className="p-3"><Badge color={p.status === "succeeded" ? "var(--ok)" : p.status === "canceled" ? "var(--risk)" : "var(--warn)"}>{p.status === "succeeded" ? "оплачен" : p.status === "canceled" ? "отменён" : "ожидает"}</Badge></td></tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </Tabs.Content>

        <Tabs.Content value="profile" className="mt-6 max-w-xl space-y-4">
          <div className="panel rounded-2xl p-5 text-[13.5px] text-muted">
            <div>Логин: <span className="text-text">{me.login}</span></div>
            <div className="mt-1">Аккаунт создан: {d(me.created_at)}</div>
            <div className="mt-1">Согласие на информационные сообщения: {me.marketing_consent ? "дано" : "не дано"}</div>
          </div>
          <div className="panel rounded-2xl p-5">
            <div className="text-[14px] font-medium">Мои данные</div>
            <p className="mt-1 text-[13px] text-muted">Выгрузите все данные, которые сервис хранит о вас, или удалите аккаунт — это также отзывает согласие на обработку.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" onClick={exportData}><Download className="size-4" /> Выгрузить данные</Button>
              <Button variant="danger" size="sm" onClick={deleteAccount}><Trash2 className="size-4" /> Удалить аккаунт</Button>
            </div>
          </div>
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="panel rounded-2xl p-8 text-center text-[13.5px] text-dim">{text}</div>;
}

function Metric({ label, value, dim }: { label: string; value: string; dim?: boolean }) {
  return (
    <div className="rounded-xl border border-line bg-panel-2/50 p-3">
      <div className="text-[11.5px] uppercase tracking-[0.12em] text-dim">{label}</div>
      <div className={cx("mt-1 text-[15px] font-medium tabular-nums", dim && "text-dim")}>{value}</div>
    </div>
  );
}

function Compare({ prev, last }: { prev: Row; last: Row }) {
  const a = prev.exposure_min || 0;
  const b = last.exposure_min || 0;
  const better = b <= a;
  return (
    <div className="rounded-xl border border-line bg-panel-2/50 p-3">
      <div className="text-[11.5px] uppercase tracking-[0.12em] text-dim">Было → стало</div>
      <div className="mt-1 flex items-center gap-2 text-[15px] font-medium tabular-nums">
        <span className="text-dim">{rub(a)}</span>
        {better ? <ArrowDownRight className="size-4 text-ok" /> : <ArrowUpRight className="size-4 text-risk" />}
        <span className={better ? "text-ok" : "text-risk"}>{rub(b)}</span>
      </div>
      <div className="text-[11.5px] text-dim">Score: {prev.score ?? "—"} → {last.score ?? "—"}</div>
    </div>
  );
}

function AuditTable({ rows }: { rows: Row[] }) {
  if (!rows.length) return <Empty text="Проверок пока нет." />;
  return (
    <div className="panel overflow-x-auto rounded-2xl">
      <table className="w-full min-w-[640px] text-left text-[13px]">
        <thead className="text-dim"><tr><th className="p-3 font-medium">Сайт</th><th className="p-3 font-medium">Дата</th><th className="p-3 font-medium">Score</th><th className="p-3 font-medium">Экспозиция</th><th className="p-3 font-medium">Статус</th><th /></tr></thead>
        <tbody>{rows.map((a) => (
          <tr key={a.id} className="border-t border-line text-muted">
            <td className="p-3 font-mono text-text">{a.host}</td><td className="p-3">{d(a.created_at)}</td>
            <td className="p-3 tabular-nums">{a.score ?? "—"}</td><td className="p-3 tabular-nums">{a.exposure_min ? `${rub(a.exposure_min)} – ${rub(a.exposure_max)}` : "—"}</td>
            <td className="p-3">{a.status === "done" ? "готово" : a.status === "failed" ? "ошибка" : "идёт"}</td>
            <td className="p-3 text-right"><Link href={`/audit/${a.id}`} className="inline-flex items-center gap-1 text-text hover:underline">Открыть <ExternalLink className="size-3.5" /></Link></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}
