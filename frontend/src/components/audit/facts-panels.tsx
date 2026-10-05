"use client";

import { FileText, Globe2, Cookie, Building2, Layers } from "lucide-react";
import * as React from "react";
import type { AuditResult } from "@/lib/types";
import { Badge, Label, cx } from "../ui";

const JUR: Record<string, { t: string; c: string }> = {
  RU: { t: "Российская компания", c: "var(--ok)" },
  foreign: { t: "Иностранная компания", c: "var(--warn)" },
  unknown: { t: "Не определено", c: "var(--unk)" },
};

function Box({ title, icon: Icon, children, className }: { title: string; icon: React.ElementType; children: React.ReactNode; className?: string }) {
  return (
    <div className={cx("panel rounded-2xl p-5", className)}>
      <div className="mb-4 flex items-center gap-2 text-[14px] font-medium"><Icon className="size-4 text-dim" /> {title}</div>
      {children}
    </div>
  );
}

export function FactsPanels({ f, full }: { f: AuditResult["facts"]; full: boolean }) {
  const cs = f.cookie_stats || { total: 0, first_party: 0, third_party: 0, analytics: 0, advertising: 0, other: 0 };
  const cd = f.company_details;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Box title="Cookies" icon={Cookie}>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
          {[["Обнаружено", cs.total], ["First-party", cs.first_party], ["Third-party", cs.third_party], ["Analytics", cs.analytics], ["Advertising", cs.advertising]].map(([k, v]) => (
            <div key={k as string} className="rounded-xl border border-line bg-panel-2/50 p-3">
              <div className="text-[22px] font-semibold tabular-nums">{v as number}</div>
              <div className="text-[11.5px] text-dim">{k}</div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[12.5px] text-dim">Уведомление о cookie: {f.cookie_banner ? "найдено" : "не найдено"}. Юридическая оценка — в разделе проверок.</p>
        {full && f.cookies.length > 0 && (
          <div className="mt-3 max-h-56 overflow-auto rounded-xl border border-line">
            <table className="w-full text-left text-[12px]">
              <thead className="sticky top-0 bg-panel-2 text-dim"><tr><th className="px-3 py-2 font-medium">Cookie</th><th className="px-3 py-2 font-medium">Домен</th><th className="px-3 py-2 font-medium">Тип</th><th className="px-3 py-2 font-medium">Сервис</th></tr></thead>
              <tbody>
                {f.cookies.map((c, i) => (
                  <tr key={i} className="border-t border-line text-muted">
                    <td className="px-3 py-1.5 font-mono">{c.name}</td><td className="px-3 py-1.5">{c.domain}</td>
                    <td className="px-3 py-1.5">{c.first_party ? "1st" : "3rd"} · {c.category}</td><td className="px-3 py-1.5">{c.service || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Box>

      <Box title="Реквизиты и тип сайта" icon={Building2}>
        <dl className="grid gap-2 text-[13px]">
          {[
            ["Тип сайта", f.site_type_ru + (f.mode === "ecommerce" ? " · режим E-COMMERCE" : "")],
            ["Наименование", cd?.names?.join("; ") || "не найдено"],
            ["ИНН", cd?.inn?.join(", ") || "—"],
            ["ОГРН / ОГРНИП", [...(cd?.ogrn || []), ...(cd?.ogrnip || [])].join(", ") || "—"],
            ["Адрес", cd?.addresses?.[0] || "не найден"],
            ["Контакты", f.contacts ? [...f.contacts.emails.slice(0, 2), ...f.contacts.phones.slice(0, 2)].join(", ") || "не найдены" : "в полном отчёте"],
          ].map(([k, v]) => (
            <div key={k} className="grid grid-cols-[130px_1fr] gap-3 border-b border-line/60 pb-2 last:border-0">
              <dt className="text-dim">{k}</dt><dd className="break-words text-muted">{v}</dd>
            </div>
          ))}
        </dl>
      </Box>

      <Box title={`Внешние сервисы (${f.external_services.length})`} icon={Globe2} className="lg:col-span-2">
        {f.external_services.length === 0 ? (
          <p className="text-[13px] text-dim">Сторонние сервисы не распознаны.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-[12.5px]">
              <thead className="text-dim"><tr><th className="pb-2 font-medium">Сервис</th><th className="pb-2 font-medium">Домен</th><th className="pb-2 font-medium">Тип</th><th className="pb-2 font-medium">Назначение</th><th className="pb-2 font-medium">Владелец</th></tr></thead>
              <tbody>
                {f.external_services.map((s) => (
                  <tr key={s.service_id} className="border-t border-line align-top text-muted">
                    <td className="py-2 pr-3 font-medium text-text">{s.name}</td>
                    <td className="py-2 pr-3 font-mono text-[11.5px]">{s.domains[0] || "в коде страницы"}</td>
                    <td className="py-2 pr-3">{s.type_ru}</td>
                    <td className="py-2 pr-3">{s.purpose}</td>
                    <td className="py-2"><Badge color={JUR[s.jurisdiction]?.c}>{JUR[s.jurisdiction]?.t}</Badge><div className="mt-1 text-[11.5px] text-dim">{s.owner}</div></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-[12px] text-dim">Юрисдикция — по компании-владельцу сервиса. Где физически хранятся данные, по домену определить нельзя: если квалификация зависит от конфигурации, она отмечена как требующая проверки.</p>
          </div>
        )}
        {f.unknown_domains.length > 0 && (
          <div className="mt-3 text-[12px] text-dim">Прочие внешние домены: <span className="font-mono">{f.unknown_domains.slice(0, 12).join(", ")}</span></div>
        )}
      </Box>

      <Box title={`Документы (${f.documents.length})`} icon={FileText}>
        {f.documents.length === 0 ? <p className="text-[13px] text-dim">Документы по ссылкам не найдены.</p> : (
          <ul className="space-y-2">
            {f.documents.slice(0, 14).map((d) => (
              <li key={d.url} className="flex items-start justify-between gap-3 text-[13px]">
                <div className="min-w-0">
                  <div className="text-muted">{d.kind_ru}</div>
                  <a href={d.url} target="_blank" rel="noopener noreferrer nofollow" className="block truncate font-mono text-[11.5px] text-dim hover:text-text">{d.url.replace(/^https?:\/\//, "")}</a>
                </div>
                <Badge color={d.accessible ? "var(--ok)" : d.accessible === false ? "var(--risk)" : "var(--unk)"}>{d.accessible ? "доступен" : d.accessible === false ? "недоступен" : "не открывался"}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Box>

      <Box title={`Проверенные страницы (${f.pages.length})`} icon={Layers}>
        <ul className="max-h-64 space-y-1.5 overflow-auto">
          {f.pages.map((p) => (
            <li key={p.url} className="flex items-center justify-between gap-3 text-[12.5px]">
              <span className="truncate font-mono text-dim">{p.url.replace(/^https?:\/\//, "")}</span>
              <span className="shrink-0 tabular-nums text-dim">{p.status}</span>
            </li>
          ))}
        </ul>
        {f.crawl && (
          <div className="mt-3 text-[12px] text-dim">
            Обход: {f.crawl.duration_s} с · сетевых запросов: {f.crawl.network_requests} · заблокировано небезопасных запросов: {f.crawl.aborted_methods}
            {f.crawl.partial ? " · обход остановлен по лимиту времени" : ""}
          </div>
        )}
      </Box>
      <div className="lg:col-span-2"><Label className="text-center">Факты собраны автоматически и не являются юридической оценкой</Label></div>
    </div>
  );
}
