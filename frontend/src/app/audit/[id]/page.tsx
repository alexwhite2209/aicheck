import type { Metadata } from "next";
import { Suspense } from "react";
import { AuditView } from "@/components/audit/audit-view";

export const metadata: Metadata = { title: "Результат проверки сайта", robots: { index: false, follow: false } };

export default async function AuditPage(props: PageProps<"/audit/[id]">) {
  const { id } = await props.params;
  return (
    <Suspense>
      <AuditView id={id} />
    </Suspense>
  );
}
