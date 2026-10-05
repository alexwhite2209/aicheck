import type { Metadata } from "next";
import { LegalDoc } from "@/components/legal-doc";

export const metadata: Metadata = { title: "Использование cookie", alternates: { canonical: "/cookies-policy" } };

export default function CookiesPolicyPage() {
  return (
    <LegalDoc title="Использование cookie" updated="03.10.2026">
      <p>Сервис использует только технические cookie, без которых невозможны вход в личный кабинет и защита от подделки запросов. Системы веб-аналитики, рекламы и сторонние трекеры не подключены, шрифты загружаются с собственного сервера.</p>
      <ul>
        <li><b>session</b> — идентификатор сессии после входа (HttpOnly, до 72 часов);</li>
        <li><b>csrf_token</b> — защита от подделки межсайтовых запросов (до 72 часов).</li>
      </ul>
      <p>Без входа в кабинет cookie не устанавливаются.</p>
    </LegalDoc>
  );
}
