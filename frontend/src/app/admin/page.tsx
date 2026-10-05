import type { Metadata } from "next";
import { AdminView } from "@/components/admin-view";

export const metadata: Metadata = { title: "Админ-панель", robots: { index: false, follow: false } };

export default function AdminPage() {
  return <AdminView />;
}
