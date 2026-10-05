export const rub = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : `${Math.round(v).toLocaleString("ru-RU").replace(/,/g, " ")} ₽`;

export const dt = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

export const d = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" }) : "—";

export const hostOf = (url: string) => {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
};

export function cn(...xs: (string | false | null | undefined)[]) {
  return xs.filter(Boolean).join(" ");
}

export const STATUS = {
  FAIL: { label: "Вероятно не выполнено", short: "Проблема", color: "var(--risk)", dot: "bg-risk", text: "text-risk" },
  REVIEW: { label: "Требует внимания", short: "Внимание", color: "var(--warn)", dot: "bg-warn", text: "text-warn" },
  PASS: { label: "Выполнено по признакам", short: "Пройдено", color: "var(--ok)", dot: "bg-ok", text: "text-ok" },
  UNKNOWN: { label: "Не удалось определить", short: "Не определено", color: "var(--unk)", dot: "bg-unk", text: "text-unk" },
  NA: { label: "Не применимо", short: "Не применимо", color: "var(--unk)", dot: "bg-unk", text: "text-unk" },
} as const;

export const SEVERITY_RU: Record<string, string> = { critical: "Критично", high: "Высокий риск", medium: "Средний", low: "Низкий", info: "Факт" };

export const STATE_RU: Record<string, string> = {
  VERIFIED_RANGE: "VERIFIED RANGE",
  ESTIMATED_RANGE: "ESTIMATED RANGE",
  NOT_DETERMINABLE: "NOT DETERMINABLE",
};
