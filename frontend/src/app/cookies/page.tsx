import { SeoPage, seoMetadata } from "@/components/seo-page";
import { SEO_PAGES } from "@/lib/seo-content";

const p = SEO_PAGES["cookies"];
export const metadata = seoMetadata(p);

export default function Page() {
  return <SeoPage p={p} />;
}