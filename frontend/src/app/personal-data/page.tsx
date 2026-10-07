import { SeoPage, seoMetadata } from "@/components/seo-page";
import { SEO_PAGES } from "@/lib/seo-content";

const p = SEO_PAGES["personal-data"];
export const metadata = seoMetadata(p);

export default function Page() {
  return <SeoPage p={p} />;
}