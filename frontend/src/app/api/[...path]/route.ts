import { NextRequest, NextResponse } from "next/server";

/* Прокси к backend: браузер общается только с этим доменом (cookie, CSRF, без CORS).
   Ключи и адрес backend не попадают на клиент. */
const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
const HOP = new Set(["host", "connection", "keep-alive", "transfer-encoding", "upgrade", "content-length", "accept-encoding"]);

async function handler(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const search = new URL(req.url).search;
  const target = `${BACKEND}/api/${path.map(encodeURIComponent).join("/")}${search}`;
  const headers = new Headers();
  // IP-заголовкам доверяем только за своим реверс-прокси (Caddy/nginx), который их перезаписывает
  const trustIp = process.env.TRUST_PROXY_HEADERS === "true";
  req.headers.forEach((v, k) => {
    const key = k.toLowerCase();
    if (HOP.has(key)) return;
    if (!trustIp && (key === "x-real-ip" || key === "x-forwarded-for")) return;
    headers.set(k, v);
  });
  const init: RequestInit = {
    method: req.method,
    headers,
    redirect: "manual",
    cache: "no-store",
    body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer(),
  };
  let res: Response;
  try {
    res = await fetch(target, init);
  } catch {
    return NextResponse.json({ detail: "Сервис проверки временно недоступен" }, { status: 503 });
  }
  const out = new Headers();
  res.headers.forEach((v, k) => {
    const key = k.toLowerCase();
    if (key === "set-cookie" || key === "content-encoding" || HOP.has(key)) return;
    out.set(k, v);
  });
  for (const c of res.headers.getSetCookie?.() ?? []) out.append("set-cookie", c);
  return new NextResponse(res.body, { status: res.status, headers: out });
}

export { handler as GET, handler as POST, handler as PUT, handler as DELETE };
export const dynamic = "force-dynamic";
