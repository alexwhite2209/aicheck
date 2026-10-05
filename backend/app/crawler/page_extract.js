() => {
  const T = (s, n = 300) => (s || "").replace(/\s+/g, " ").trim().slice(0, n);
  const abs = (h) => { try { return new URL(h, location.href).href; } catch (e) { return ""; } };
  const visible = (el) => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
  const inFooter = (el) => !!el.closest("footer, [class*=footer], [id*=footer], [class*=Footer]");

  const labelFor = (el) => {
    let t = "";
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l) t = l.innerText;
    }
    if (!t) { const l = el.closest("label"); if (l) t = l.innerText; }
    if (!t) t = el.getAttribute("aria-label") || "";
    if (!t) {
      const lb = el.getAttribute("aria-labelledby");
      if (lb) t = lb.split(" ").map((i) => (document.getElementById(i) || {}).innerText || "").join(" ");
    }
    if (!t && el.type === "checkbox") {
      // текст рядом с чекбоксом (частая вёрстка без label)
      const p = el.parentElement;
      if (p) t = p.innerText;
      if ((!t || t.length < 5) && p && p.parentElement) t = p.parentElement.innerText;
    }
    if (!t) {
      const prev = el.previousElementSibling;
      if (prev && prev.innerText && prev.innerText.length < 80) t = prev.innerText;
    }
    return T(t, 700);
  };

  const linksIn = (root) => Array.from(root.querySelectorAll("a[href]")).slice(0, 30).map((a) => ({ href: abs(a.getAttribute("href")), text: T(a.innerText || a.title, 160) }));

  const fieldInfo = (el) => {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || (tag === "textarea" ? "textarea" : tag === "select" ? "select" : "text")).toLowerCase();
    const label = labelFor(el);
    const info = {
      tag, type, name: el.getAttribute("name") || "", id: el.id || "",
      placeholder: T(el.getAttribute("placeholder"), 120), autocomplete: el.getAttribute("autocomplete") || "",
      label, required: el.required || el.getAttribute("aria-required") === "true" || /\*\s*$/.test(label),
      visible: visible(el),
    };
    if (type === "checkbox" || type === "radio") {
      info.checked_default = el.hasAttribute("checked");
      const scope = el.closest("label") || el.parentElement || el;
      info.links = linksIn(scope.parentElement || scope);
      info.value = T(el.value, 60);
    }
    return info;
  };

  const consentRe = /(согла|персональн|конфиденциальн|политик|обработк|privacy|policy|оферт)/i;
  const formInfo = (root, index, isForm) => {
    const fields = Array.from(root.querySelectorAll("input, textarea, select"))
      .filter((el) => !["submit", "button", "image", "reset"].includes((el.getAttribute("type") || "").toLowerCase()))
      .slice(0, 60).map(fieldInfo);
    const hidden = fields.filter((f) => f.type === "hidden").map((f) => f.name).slice(0, 20);
    const btns = Array.from(root.querySelectorAll("button, input[type=submit], [role=button], a.btn, a[class*=button]"));
    const texts = [];
    root.querySelectorAll("p, span, div, small, label, a").forEach((el) => {
      if (texts.length > 12) return;
      if (el.children.length > 4) return;
      const t = T(el.innerText, 600);
      if (t && t.length > 15 && consentRe.test(t) && !texts.includes(t)) texts.push(t);
    });
    let html = root.outerHTML.replace(/<script[\s\S]*?<\/script>/gi, "").replace(/<style[\s\S]*?<\/style>/gi, "").replace(/<svg[\s\S]*?<\/svg>/gi, "<svg/>");
    return {
      index, is_form: isForm,
      action: isForm ? (root.getAttribute("action") ? abs(root.getAttribute("action")) : "") : "",
      method: isForm ? (root.getAttribute("method") || "get").toLowerCase() : "",
      dom_id: root.id || "", dom_class: T(root.className && root.className.baseVal === undefined ? root.className : "", 120),
      fields: fields.filter((f) => f.type !== "hidden"), hidden_names: hidden,
      submit_text: T(btns.map((b) => b.innerText || b.value || "").join(" | "), 160),
      consent_texts: texts, links: linksIn(root),
      heading: T(((root.closest("section, div") || root).querySelector("h1, h2, h3, h4") || {}).innerText || "", 160),
      visible: visible(root),
      html: html.slice(0, 2500),
    };
  };

  // формы: <form> + группы полей вне <form> (SPA, конструкторы)
  const forms = [];
  Array.from(document.forms).slice(0, 25).forEach((f, i) => forms.push(formInfo(f, i, true)));
  const orphanRoots = new Set();
  document.querySelectorAll("input:not([type=hidden]):not([type=submit]):not([type=button]), textarea").forEach((el) => {
    if (el.form || el.closest("form")) return;
    let node = el.parentElement;
    for (let d = 0; node && d < 6; d++, node = node.parentElement) {
      if (node.querySelector("button, [type=submit], [role=button]")) { orphanRoots.add(node); break; }
    }
  });
  Array.from(orphanRoots).filter((n) => !Array.from(orphanRoots).some((o) => o !== n && o.contains(n))).slice(0, 10)
    .forEach((n, i) => forms.push(formInfo(n, 100 + i, false)));

  const links = Array.from(document.querySelectorAll("a[href]")).slice(0, 600).map((a) => ({
    href: abs(a.getAttribute("href")), text: T(a.innerText || a.title || a.getAttribute("aria-label"), 160),
    footer: inFooter(a), rel: a.getAttribute("rel") || "",
  })).filter((l) => l.href && !l.href.startsWith("javascript:"));

  const scripts = Array.from(document.scripts).slice(0, 200);
  const scriptSrc = scripts.filter((s) => s.src).map((s) => s.src);
  const inline = scripts.filter((s) => !s.src && s.textContent).map((s) => s.textContent.slice(0, 4000)).join("\n").slice(0, 120000);

  const ld = [];
  document.querySelectorAll('script[type="application/ld+json"]').forEach((s) => {
    try {
      const walk = (o) => {
        if (!o || typeof o !== "object") return;
        if (Array.isArray(o)) return o.forEach(walk);
        if (o["@type"]) [].concat(o["@type"]).forEach((t) => ld.push(String(t)));
        if (o["@graph"]) walk(o["@graph"]);
      };
      walk(JSON.parse(s.textContent));
    } catch (e) {}
  });
  document.querySelectorAll("[itemtype]").forEach((el) => ld.push((el.getAttribute("itemtype") || "").split("/").pop()));

  // уведомление о cookie: видимые fixed/sticky блоки с упоминанием cookie
  let cookieBanner = null;
  for (const el of Array.from(document.querySelectorAll("body *")).slice(0, 4000)) {
    const st = getComputedStyle(el);
    if (!(st.position === "fixed" || st.position === "sticky") || !visible(el)) continue;
    const t = el.innerText || "";
    if (/cookie|куки|кук[иа]-?файл/i.test(t) && t.length < 1500) {
      const buttons = Array.from(el.querySelectorAll("button, a, [role=button]")).map((b) => T(b.innerText, 40)).filter(Boolean);
      cookieBanner = { text: T(t, 400), buttons: buttons.slice(0, 6), links: linksIn(el) };
      break;
    }
  }

  // признаки рекламы
  const adLabels = Array.from(document.querySelectorAll("span, div, small, p, a, b")).filter((el) => el.children.length === 0 && /^\s*(реклама|на правах рекламы)\.?\s*$/i.test(el.innerText || "")).length;
  const eridLinks = links.filter((l) => /[?&]erid=/i.test(l.href)).map((l) => l.href).slice(0, 20);
  const adSlots = document.querySelectorAll("ins.adsbygoogle, [id^=yandex_rtb], [id^=adfox], [id*=adfox_], div[data-ad-slot], [class*=yandex-rtb]").length;
  const bannerCands = [];
  const NOT_AD = /ymaps|ym-|informer|metrika|counter|map|leaflet|footer-logo|payment|pay-|social|share|messenger/i;
  const NOT_AD_HREF = /metrika\.yandex|yandex\.(ru|com)\/maps|2gis\.|google\.[a-z.]+\/maps|liveinternet|top\.mail\.ru|vk\.com|t\.me|wa\.me|ok\.ru|youtube\.com|instagram|dzen\.ru/i;
  document.querySelectorAll("a[href] img").forEach((img) => {
    const a = img.closest("a");
    const cont = img.closest("[class*=banner], [id*=banner], [class*=promo], [class*=adv], [class*=reklam], [class*=sponsor], [class*=partner], aside");
    if (!a || !cont) return;
    const cls = String(cont.className && cont.className.baseVal === undefined ? cont.className : "") + " " + (cont.id || "");
    if (NOT_AD.test(cls) || img.closest("[class*=ymaps], [class*=informer], [class*=map]")) return;
    const r = img.getBoundingClientRect();
    if ((img.naturalWidth || r.width) < 120 || (img.naturalHeight || r.height) < 50) return; // иконки и счётчики — не баннеры
    const href = abs(a.getAttribute("href"));
    if (NOT_AD_HREF.test(href)) return;
    try { if (new URL(href).hostname === location.hostname) return; } catch (e) { return; }
    if (bannerCands.length < 10) bannerCands.push({ href, alt: T(img.alt, 100), container: T(cont.className || cont.id || cont.tagName, 80), label_near: /реклама/i.test((cont.innerText || "")) });
  });

  const iframes = Array.from(document.querySelectorAll("iframe")).slice(0, 40).map((f) => abs(f.getAttribute("src") || f.getAttribute("data-src") || "")).filter(Boolean);
  const meta = (n) => (document.querySelector(`meta[name="${n}"], meta[property="${n}"]`) || {}).content || "";
  const bodyText = (document.body ? document.body.innerText : "").slice(0, 150000);
  const footerEl = document.querySelector("footer, [class*=footer], [id*=footer]");

  return {
    title: T(document.title, 200), lang: document.documentElement.lang || "",
    meta: { description: T(meta("description"), 300), generator: T(meta("generator"), 100), og_type: meta("og:type") },
    text: bodyText, footer_text: footerEl ? T(footerEl.innerText, 4000) : "",
    links, forms, scripts: scriptSrc.slice(0, 150), inline_scripts: inline, iframes, ld_types: Array.from(new Set(ld)).slice(0, 40),
    cookie_banner: cookieBanner,
    ads: { labels: adLabels, erid_links: eridLinks, slots: adSlots, banners: bannerCands },
    counts: { elements: document.getElementsByTagName("*").length, images: document.images.length },
  };
}
