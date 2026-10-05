import type { MetadataRoute } from "next";
import { BRAND } from "@/components/brand";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/api/", "/audit/", "/account", "/admin", "/login", "/register"] }],
    sitemap: `${BRAND.url}/sitemap.xml`,
    host: BRAND.url,
  };
}
