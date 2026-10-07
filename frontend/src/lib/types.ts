export type Stage = { key: string; label: string; status: "pending" | "running" | "done" | "error" | "skipped"; detail: string; at: string | null };

export type StatusResp = { id: string; url: string; status: "queued" | "running" | "done" | "failed"; stages: Stage[]; error: string | null };

export type Basis = {
  id: string; key?: string; label: string; act: string; act_title?: string; article: string; part: string; paragraph: string; title: string;
  text?: string; edition: string; effective_from?: string | null; checked_at?: string; official_url: string;
};

export type Finance = {
  state: "VERIFIED_RANGE" | "ESTIMATED_RANGE" | "NOT_DETERMINABLE"; rule_id: string; legal_basis?: string; calculation_method?: string;
  min_value?: number; max_value?: number; date?: string; bucket?: "main" | "potential"; reason?: string;
};

export type Result = {
  rule_id: string; version: number; title: string; category: string; severity: string; status: "PASS" | "FAIL" | "REVIEW" | "UNKNOWN" | "NA";
  status_ru: string; confidence: string; confidence_ru: string; fact: string; evidence: { page: string; label: string; snippet: string }[];
  basis: Basis[]; why: string; fix: string; finance: Finance;
};

export type Exposure = {
  state: Finance["state"]; min: number; max: number; items: Finance[]; potential: { min: number; max: number; items: Finance[] };
  note: string; subject_type: string; subject_ru: string;
};

export type Service = { service_id: string; name: string; type: string; type_ru: string; purpose: string; owner: string; jurisdiction: string; domains: string[]; found_on: string[] };

export type AuditResult = {
  id: string; url: string; host: string; status: string; created_at: string; finished_at: string; score: number | null;
  counts: { fail: number; review: number; pass: number; unknown: number; na: number };
  exposure: { state: string; min: number; max: number } | null; exposure_full: Exposure; full_access: boolean; paywall: boolean; owned: boolean;
  results: Result[]; ai: { used?: boolean; summary?: string | null; items: Record<string, { explanation?: string | null; recommendation?: string | null }>; locked?: boolean; policy_remarks?: string[]; model?: string };
  facts: {
    site_type: string; site_type_ru: string; mode: string; final_url: string; https: Record<string, unknown>; pages: { url: string; title: string; status: number; depth: number }[];
    cookie_stats: { total: number; first_party: number; third_party: number; analytics: number; advertising: number; other: number } | null;
    cookie_banner: boolean; external_services: Service[]; unknown_domains: string[];
    documents: { kind: string; kind_ru: string; url: string; link_text: string; accessible: boolean | null; status: number | null; source: string; text_len: number }[];
    forms: { ref: string; page: string; purpose: string; pd_kinds: string[]; special_kinds: string[]; has_pd: boolean; has_consent_mechanism: boolean; external_handler: { name: string } | null; fields: { label: string; kind: string | null; required: boolean }[] }[];
    company_details: { inn: string[]; ogrn: string[]; ogrnip: string[]; names: string[]; addresses: string[]; subject_type: string } | null;
    contacts: { emails: string[]; phones: string[] } | null;
    ecommerce_signals: { signal: string; evidence: string }[];
    crawl: { pages: number; duration_s: number; partial: boolean; errors: { url: string; error: string }[]; blocked: unknown[]; aborted_methods: number; network_requests: number } | null;
    cookies: { name: string; domain: string; first_party: boolean; category: string; service: string | null; expires_days: number | null }[];
  };
  snapshot: { date: string; engine: string; rules: { rule_id: string; version: number }[]; articles: Record<string, string> };
  disclaimer: string;
  deep?: boolean;
  security?: SecurityBlock | null;
  registries?: Registries | null;
};

export type SecFinding = {
  id: string; skill: string; category: string; title: string; severity: string; status: "FAIL" | "REVIEW" | "PASS" | "INFO";
  fact: string; recommendation: string; evidence: { page: string; label: string; snippet: string }[]; touches_pd: boolean; confidence: string;
  tech?: string; legal_basis?: Basis; legal_note?: string;
};

export type SecurityBlock = {
  locked?: boolean;
  score: number | null;
  counts: { fail: number; review: number; pass: number; info: number };
  by_severity?: Record<string, number>;
  findings: SecFinding[];
  disclaimer?: string;
  active_available?: boolean;
};

export type Registries = {
  domain: { available: boolean; registered?: boolean; domain?: string; registrar?: string; created?: string; expires?: string; age_years?: number | null; note?: string; link?: string };
  egrul: { available: boolean; found?: boolean; name?: string; ogrn?: string; status?: string; kind?: string; address?: string; inn?: string; manual?: boolean; free?: boolean; link?: string; note?: string };
  rkn: { available: boolean; free?: boolean; note?: string; registries: { id: string; title: string; why: string; link: string; captcha: boolean }[] };
  note?: string;
};
