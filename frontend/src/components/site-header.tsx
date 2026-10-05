"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";
import { api } from "@/lib/api";
import { Logo } from "./brand";
import { Button, cx } from "./ui";

type Me = { user: { email: string; role: string } };

const NAV = [
  { href: "/#how", label: "Как это работает" },
  { href: "/methodology", label: "Методика" },
  { href: "/pricing", label: "Тарифы" },
  { href: "/faq", label: "FAQ" },
];

export function SiteHeader() {
  const [me, setMe] = React.useState<Me["user"] | null | undefined>(undefined);
  const [scrolled, setScrolled] = React.useState(false);
  const path = usePathname();
  React.useEffect(() => {
    api<Me>("/api/auth/me").then((r) => setMe(r.user)).catch(() => setMe(null));
  }, [path]);
  React.useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  return (
    <header className={cx("sticky top-0 z-40 transition-colors duration-300", scrolled ? "border-b border-line bg-bg/75 backdrop-blur-xl" : "border-b border-transparent")}>
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className="rounded-lg px-3 py-1.5 text-[13.5px] text-muted transition hover:bg-white/[0.04] hover:text-text">
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {me === undefined ? null : me ? (
            <>
              {me.role === "admin" && (
                <Button asChild variant="ghost" size="sm">
                  <Link href="/admin">Админ</Link>
                </Button>
              )}
              <Button asChild variant="secondary" size="sm">
                <Link href="/account">Кабинет</Link>
              </Button>
            </>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
                <Link href="/login">Войти</Link>
              </Button>
              <Button asChild variant="secondary" size="sm">
                <Link href="/register">Регистрация</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
