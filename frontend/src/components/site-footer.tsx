import Link from "next/link";
import { DISCLAIMER, Logo } from "./brand";

const COLS = [
  {
    title: "Проверки",
    links: [
      ["/proverka-saita", "Проверка сайта"],
      ["/audit-152-fz", "Аудит по 152-ФЗ"],
      ["/personal-data", "Персональные данные"],
      ["/cookies", "Cookies и аналитика"],
      ["/reklama", "Маркировка рекламы"],
      ["/internet-magazin", "Интернет-магазин"],
    ],
  },
  {
    title: "Сервис",
    links: [
      ["/methodology", "Методика и нормы"],
      ["/pricing", "Тарифы"],
      ["/faq", "Вопросы и ответы"],
      ["/account", "Личный кабинет"],
    ],
  },
  {
    title: "Документы",
    links: [
      ["/privacy", "Политика обработки ПД"],
      ["/consent", "Согласие на обработку ПД"],
      ["/terms", "Пользовательское соглашение"],
      ["/cookies-policy", "Использование cookie"],
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="relative mt-24 border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div className="space-y-4">
          <Logo />
          <p className="max-w-xs text-[13px] leading-relaxed text-dim">
            Автоматическая проверка публичной части сайта на соответствие применимым требованиям законодательства РФ.
          </p>
        </div>
        {COLS.map((c) => (
          <div key={c.title}>
            <div className="mb-3 text-[12px] font-medium uppercase tracking-[0.14em] text-dim">{c.title}</div>
            <ul className="space-y-2">
              {c.links.map(([href, label]) => (
                <li key={href}>
                  <Link href={href} className="text-[13.5px] text-muted transition hover:text-text">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-line">
        <div className="mx-auto max-w-6xl px-4 py-6 text-[12px] leading-relaxed text-dim sm:px-6">
          <p>{DISCLAIMER}</p>
          <p className="mt-2">© 2026 Норма</p>
        </div>
      </div>
    </footer>
  );
}
