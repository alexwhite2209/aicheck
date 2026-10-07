import type { Metadata } from "next";
import { AccountView } from "@/components/account-view";

export const metadata: Metadata = { title: "Личный кабинет", robots: { index: false } };

export default function AccountPage() {
  return <AccountView />;
}
