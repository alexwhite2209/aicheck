"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { api } from "@/lib/api";
import { Button, Checkbox, Input, Label } from "./ui";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const [login, setLogin] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [consent, setConsent] = React.useState(false);
  const [marketing, setMarketing] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState("");
  const router = useRouter();
  const params = useSearchParams();
  const claim = params.get("claim");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    if (mode === "register" && !consent) {
      setErr("Без согласия на обработку персональных данных регистрация невозможна");
      return;
    }
    setBusy(true);
    try {
      await api(`/api/auth/${mode}`, { method: "POST", body: mode === "register" ? { login, password, consent, marketing } : { login, password } });
      if (claim) {
        try {
          await api(`/api/user/audits/${claim}/claim`, { method: "POST" });
        } catch {}
        router.push(`/audit/${claim}`);
      } else router.push("/account");
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ошибка");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-20">
      <div className="panel rounded-3xl p-7 sm:p-8">
        <Label>{mode === "login" ? "Вход" : "Регистрация"}</Label>
        <h1 className="mt-2 text-[24px] font-semibold tracking-tight">{mode === "login" ? "С возвращением" : "Сохраняйте сайты и историю проверок"}</h1>
        {claim && <p className="mt-2 text-[13px] text-muted">После {mode === "login" ? "входа" : "регистрации"} проверка будет сохранена в кабинете.</p>}
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="login" className="mb-1.5 block text-[13px] text-muted">Логин{mode === "register" ? " (3–32 символа: латиница, цифры, _ . -)" : ""}</label>
            <Input id="login" type="text" autoComplete="username" required minLength={mode === "register" ? 3 : 1} maxLength={32} autoCapitalize="none" spellCheck={false} value={login} onChange={(e) => setLogin(e.target.value)} />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-[13px] text-muted">Пароль{mode === "register" ? " (не менее 8 символов)" : ""}</label>
            <Input id="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "register" ? 8 : 1} value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {mode === "register" && (
            <div className="space-y-3 pt-1">
              <Checkbox id="consent" checked={consent} onChange={setConsent}>
                Даю <Link href="/consent" target="_blank" className="text-text underline underline-offset-2">согласие на обработку персональных данных</Link> (логин и технические данные) для работы личного кабинета. Обязательно.
              </Checkbox>
              <Checkbox id="marketing" checked={marketing} onChange={setMarketing}>
                Согласен получать сообщения о новых возможностях сервиса и изменениях законодательства. Необязательно, можно отозвать.
              </Checkbox>
              <p className="text-[12px] leading-relaxed text-dim">
                Порядок обработки описан в <Link href="/privacy" target="_blank" className="underline underline-offset-2">политике обработки персональных данных</Link>.
              </p>
            </div>
          )}
          {err && <div className="text-[13px] text-risk">{err}</div>}
          <Button type="submit" variant="primary" size="lg" className="w-full" disabled={busy}>
            {mode === "login" ? "Войти" : "Зарегистрироваться"}
          </Button>
        </form>
        <div className="mt-5 text-center text-[13px] text-dim">
          {mode === "login" ? (
            <>Нет аккаунта? <Link href={`/register${claim ? `?claim=${claim}` : ""}`} className="text-text underline underline-offset-2">Регистрация</Link></>
          ) : (
            <>Уже есть аккаунт? <Link href={`/login${claim ? `?claim=${claim}` : ""}`} className="text-text underline underline-offset-2">Войти</Link></>
          )}
        </div>
      </div>
    </div>
  );
}
