import Link from "next/link";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link href="/" className={`group inline-flex items-center gap-2.5 ${className}`} aria-label="Норма — на главную">
      <span className="relative grid size-7 place-items-center rounded-[9px] border border-white/15 bg-gradient-to-b from-white/[0.12] to-white/[0.02] shadow-[0_0_24px_-6px_rgba(168,190,255,0.5)]">
        <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M5 12.5l4.2 4.2L19 7" />
          <path d="M5 4.5h14" className="opacity-40" />
        </svg>
      </span>
      <span className="text-[15px] font-semibold tracking-tight">Норма</span>
    </Link>
  );
}

export const BRAND = {
  name: "Норма",
  tagline: "Российский AI-аудит сайта",
  url: process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
};

export const DISCLAIMER =
  "Автоматизированный аудит является информационным инструментом и не является юридическим заключением. Результаты основаны на данных, доступных сервису в момент проверки, и не заменяют консультацию квалифицированного специалиста.";
