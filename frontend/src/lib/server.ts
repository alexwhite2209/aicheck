import "server-only";

const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";

export async function backend<T>(path: string, revalidate = 300): Promise<T | null> {
  try {
    const r = await fetch(`${BACKEND}${path}`, { next: { revalidate } });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}
