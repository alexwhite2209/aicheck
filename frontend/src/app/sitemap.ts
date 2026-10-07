import type { MetadataRoute } from "next";
import { BRAND } from "@/components/brand";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date("2026-10-03");
  const pages: [string, number][] = [
    ["", 1], ["/proverka-saita", 0.9], ["/audit-152-fz", 0.9], ["/personal-data", 0.8], ["/cookies", 0.8], ["/reklama", 0.8],
    ["/internet-magazin", 0.8], ["/pricing", 0.7], ["/faq", 0.6], ["/methodology", 0.6], ["/privacy", 0.3], ["/consent", 0.3], ["/terms", 0.3], ["/cookies-policy", 0.2],
  ];
  return pages.map(([p, priority]) => ({ url: `${BRAND.url}${p}`, lastModified: now, changeFrequency: "weekly", priority }));
}
