import { ImageResponse } from "next/og";

export const alt = "Норма — проверка сайта на соответствие законодательству РФ";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", padding: 72, background: "#060709", color: "#f1f2f4", fontFamily: "sans-serif" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 30, fontWeight: 600 }}>
          <div style={{ width: 48, height: 48, borderRadius: 14, border: "1px solid rgba(255,255,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#f1f2f4" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.2 4.2L19 7" /></svg>
          </div>
          Норма
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontSize: 22, letterSpacing: 4, color: "#9198a3" }}>РОССИЙСКИЙ AI-АУДИТ САЙТА</div>
          <div style={{ fontSize: 64, fontWeight: 700, lineHeight: 1.08, maxWidth: 980 }}>Проверьте сайт на соответствие законодательству РФ</div>
        </div>
        <div style={{ display: "flex", gap: 28, fontSize: 24, color: "#9198a3" }}>
          <span>152-ФЗ</span><span>149-ФЗ</span><span>38-ФЗ</span><span>Защита прав потребителей</span>
        </div>
      </div>
    ),
    size,
  );
}
