"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, Circle, Loader2, Minus, X } from "lucide-react";
import * as React from "react";
import type { Stage } from "@/lib/types";
import { Spotlight } from "../effects";
import { cx } from "../ui";

export function Progress({ url, stages, startedAt }: { url: string; stages: Stage[]; startedAt: number }) {
  const [now, setNow] = React.useState(() => Date.now());
  React.useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(t);
  }, []);
  const done = stages.filter((s) => s.status === "done").length;
  const pct = stages.length ? Math.round((done / stages.length) * 100) : 0;
  const crawl = ["connect", "https", "html", "dom", "pages", "documents", "forms", "external", "cookies", "analytics", "pd"];
  const first = stages.filter((s) => crawl.includes(s.key));
  const last = stages.filter((s) => !crawl.includes(s.key));
  const elapsed = Math.max(0, Math.floor((now - startedAt) / 1000));

  return (
    <div className="mx-auto max-w-2xl px-4 py-16 sm:py-24">
      <div className="panel noise relative overflow-hidden rounded-3xl p-6 sm:p-9">
        <Spotlight size={500} />
        <motion.div aria-hidden className="pointer-events-none absolute inset-x-0 h-24 bg-gradient-to-b from-transparent via-white/[0.035] to-transparent"
          animate={{ top: ["-20%", "110%"] }} transition={{ duration: 3.2, repeat: Infinity, ease: "linear" }} />
        <div className="relative">
          <div className="flex items-center justify-between gap-4">
            <div className="text-[12px] font-semibold uppercase tracking-[0.2em] text-muted">Проверяем сайт</div>
            <div className="font-mono text-[12px] tabular-nums text-dim">{String(Math.floor(elapsed / 60)).padStart(2, "0")}:{String(elapsed % 60).padStart(2, "0")}</div>
          </div>
          <div className="mt-3 break-all font-mono text-[17px] text-text sm:text-[19px]">{url}</div>
          <div className="mt-5 h-1 overflow-hidden rounded-full bg-white/[0.06]">
            <motion.div className="h-full rounded-full bg-white/80" animate={{ width: `${pct}%` }} transition={{ duration: 0.6, ease: "easeOut" }} />
          </div>
          <ul className="mt-7 space-y-1">
            {first.map((s) => <Row key={s.key} s={s} />)}
          </ul>
          <div className="hairline my-4" />
          <ul className="space-y-1">
            {last.map((s) => <Row key={s.key} s={s} big />)}
          </ul>
          <p className="mt-7 text-[12.5px] leading-relaxed text-dim">
            Этапы отображают реальный ход проверки. Обычно она занимает 30–120 секунд: сервис открывает до 20 страниц, выполняет JavaScript и не отправляет формы.
          </p>
        </div>
      </div>
    </div>
  );
}

function Row({ s, big }: { s: Stage; big?: boolean }) {
  const icon = {
    done: <Check className="size-3.5 text-ok" strokeWidth={3} />,
    running: <Loader2 className="size-3.5 animate-spin text-text" />,
    pending: <Circle className="size-3 text-dim/60" />,
    error: <X className="size-3.5 text-risk" strokeWidth={3} />,
    skipped: <Minus className="size-3.5 text-dim" />,
  }[s.status];
  return (
    <motion.li layout className={cx("flex items-start gap-3 rounded-lg px-2 py-1.5 transition-colors", s.status === "running" && "bg-white/[0.035]")}>
      <span className={cx("mt-[3px] grid size-5 shrink-0 place-items-center rounded-full border", s.status === "done" ? "border-ok/30 bg-ok/10" : s.status === "running" ? "border-white/25 pulse-dot" : "border-line-2")}>
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className={cx("text-[14px]", s.status === "pending" ? "text-dim" : "text-text", big && "font-medium")}>{s.label}</div>
        <AnimatePresence>
          {s.detail ? (
            <motion.div initial={{ opacity: 0, y: -3 }} animate={{ opacity: 1, y: 0 }} className="truncate text-[12.5px] text-dim">
              {s.detail}
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </motion.li>
  );
}
