"use client";

import { ArrowRight, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { api } from "@/lib/api";
import { Magnetic } from "./effects";
import { Button, cx } from "./ui";

export function UrlForm({ size = "lg", autoFocus = false }: { size?: "lg" | "md"; autoFocus?: boolean }) {
  const [url, setUrl] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState("");
  const [focus, setFocus] = React.useState(false);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    const v = url.trim();
    if (!v || !/\./.test(v)) {
      setErr("Введите адрес сайта, например example.ru");
      return;
    }
    setBusy(true);
    try {
      const r = await api<{ id: string }>("/api/audit", { method: "POST", body: { url: v } });
      router.push(`/audit/${r.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Не удалось запустить проверку");
      setBusy(false);
    }
  }

  const big = size === "lg";
  return (
    <form onSubmit={submit} className="w-full" noValidate>
      <div
        className={cx(
          "relative flex flex-col gap-2 rounded-2xl border bg-panel/80 p-2 backdrop-blur-md transition-all duration-300 sm:flex-row sm:items-center",
          focus ? "border-white/25 glow-ring" : "border-line-2",
          big && "border-beam",
        )}
      >
        <div className="flex min-w-0 flex-1 items-center gap-2 px-3">
          <span className="select-none font-mono text-[13px] text-dim">https://</span>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value.replace(/^https?:\/\//i, ""))}
            onFocus={() => setFocus(true)}
            onBlur={() => setFocus(false)}
            autoFocus={autoFocus}
            inputMode="url"
            autoComplete="url"
            spellCheck={false}
            placeholder="example.ru"
            aria-label="Адрес сайта"
            className={cx("min-w-0 flex-1 bg-transparent font-mono text-text outline-none placeholder:text-dim/70", big ? "h-12 text-[16px]" : "h-10 text-[14px]")}
          />
        </div>
        <Magnetic>
          <Button type="submit" variant="primary" size={big ? "xl" : "lg"} disabled={busy} className="w-full uppercase sm:w-auto">
            {busy ? <Loader2 className="size-4 animate-spin" /> : null}
            Проверить сайт
            {!busy && <ArrowRight className="size-4" />}
          </Button>
        </Magnetic>
      </div>
      <div className="mt-3 min-h-5 text-center text-[13px]">{err ? <span className="text-risk">{err}</span> : null}</div>
    </form>
  );
}
