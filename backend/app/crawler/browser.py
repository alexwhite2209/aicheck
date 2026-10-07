"""Краулер на Playwright: открывает сайт в Chromium через egress-прокси и собирает сырые данные."""
import asyncio
import io
import logging
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit

from ..config import get_settings
from .egress_proxy import EgressProxy

log = logging.getLogger(__name__)
EXTRACT_JS = (Path(__file__).parent / "page_extract.js").read_text(encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36 NormaAuditBot/1.0 (+https://norma-audit.ru/bot)")

# Не переходим: админки, выход, удаление, корзина/checkout, личные кабинеты, изменение данных
DANGEROUS_RE = re.compile(
    r"(/admin|/administrator|/wp-admin|/wp-login|/bitrix/admin|/user/login|/login|/signin|/sign-in|/logout|/log-out|/signout|"
    r"/exit|/delete|/remove|/edit|/update|/checkout|/cart|/basket|/korzina|/order|/zakaz|/account|/cabinet|/kabinet|/lk/|/lk$|"
    r"/personal/|/profile|/my/|/register|/registration|/password|/unsubscribe|/subscribe/confirm|/oauth|/auth|/api/|/feed|/rss|"
    r"/search|/wp-json|/xmlrpc|/cdn-cgi/|action=|logout|add-to-cart|add_to_cart|remove_item|delete=|\?add=|token=|sessid=)",
    re.I)
SKIP_EXT_RE = re.compile(r"\.(jpe?g|png|gif|webp|svg|ico|mp4|webm|mp3|wav|avi|mov|zip|rar|7z|gz|exe|dmg|apk|css|js|woff2?|ttf|xml)(\?|$)", re.I)
DOC_EXT_RE = re.compile(r"\.(pdf|docx?|rtf|odt|txt)(\?|$)", re.I)
PRIORITY_RE = re.compile(
    r"(политик|конфиденциал|персональн|privacy|policy|politik|soglas|согласи|consent|оферт|oferta|offer|договор|"
    r"usloviya|условия|terms|соглашени|cookie|куки|контакт|contact|kontakt|реквизит|rekvizit|о-компании|о компании|about|o-nas|"
    r"доставк|delivery|dostavka|оплат|payment|oplata|возврат|vozvrat|return|обмен|рекомендательн|legal|docs|документ)", re.I)
POLICY_PROBES = ("/privacy", "/privacy-policy", "/policy", "/politika-konfidencialnosti", "/politika", "/personal-data",
                 "/privacy/", "/policy/")

Stage = Callable[[str, str, str], Awaitable[None]]


def _same_site(host: str, root: str) -> bool:
    strip = lambda h: h[4:] if h.startswith("www.") else h  # noqa: E731
    return strip(host) == strip(root)


def _clean_url(u: str) -> str:
    u, _ = urldefrag(u)
    return u


async def crawl(start_url: str, stage: Stage, deep: bool = False) -> dict:
    """Возвращает словарь с сырыми данными обхода. Сеть — только через EgressProxy.

    deep=True дополнительно собирает данные для платного модуля безопасности (безопасные GET).
    """
    from playwright.async_api import Error as PWError, async_playwright

    st = get_settings()
    started = time.monotonic()
    deadline = started + st.total_timeout - 10
    allow = set(filter(None, (getattr(st, "crawler_test_allowlist", "") or "").split(","))) if not st.is_prod else set()
    proxy = EgressProxy(test_allowlist=allow)
    await proxy.start()

    result: dict = {
        "start_url": start_url, "final_url": start_url, "pages": [], "network": [], "cookies": [], "errors": [],
        "https": {}, "documents_fetched": [], "probes": [], "blocked": proxy.blocked, "aborted_methods": [],
        "main_html": "", "redirect_chain": [], "partial": False, "main_headers": {}, "security": None,
    }
    network: list[dict] = result["network"]
    root_host = urlsplit(start_url).hostname or ""

    async def route_handler(route):
        req = route.request
        if req.method not in ("GET", "HEAD", "OPTIONS"):
            if len(result["aborted_methods"]) < 100:
                result["aborted_methods"].append({"method": req.method, "url": req.url[:300]})
            await route.abort("blockedbyclient")
            return
        if req.resource_type in ("media",):
            network.append({"url": req.url[:1000], "type": req.resource_type, "method": req.method, "aborted": True})
            await route.abort("blockedbyclient")
            return
        await route.continue_()

    def on_request(req):
        if len(network) < 3000:
            network.append({"url": req.url[:1000], "type": req.resource_type, "method": req.method})

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            proxy={"server": proxy.url, "bypass": "<-loopback>"},
            args=["--proxy-bypass-list=<-loopback>", "--disable-dev-shm-usage", "--no-first-run",
                  "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                  "--webrtc-ip-handling-policy=disable_non_proxied_udp", "--disable-background-networking",
                  "--disable-features=DnsOverHttps,NetworkPrediction"],
        )

        async def new_context(ignore_tls: bool):
            ctx = await browser.new_context(
                user_agent=UA, locale="ru-RU", timezone_id="Europe/Moscow", viewport={"width": 1366, "height": 900},
                ignore_https_errors=ignore_tls, service_workers="block", accept_downloads=False,
            )
            ctx.set_default_navigation_timeout(st.page_timeout * 1000)
            ctx.set_default_timeout(st.page_timeout * 1000)
            await ctx.route("**/*", route_handler)
            ctx.on("request", on_request)
            return ctx

        try:
            # ---------- 1. Подключение
            await stage("connect", "running", "")
            ctx = await new_context(False)
            page = await ctx.new_page()
            cert_valid = True
            t0 = time.monotonic()
            try:
                resp = await page.goto(start_url, wait_until="domcontentloaded")
            except PWError as e:
                msg = str(e)
                if "ERR_CERT" in msg or "SSL" in msg:
                    cert_valid = False
                    await ctx.close()
                    ctx = await new_context(True)
                    page = await ctx.new_page()
                    resp = await page.goto(start_url, wait_until="domcontentloaded")
                elif start_url.startswith("https://") and ("ERR_CONNECTION" in msg or "ERR_TIMED_OUT" in msg or "ERR_SSL" in msg):
                    # сайт без HTTPS — пробуем HTTP
                    start_url = "http://" + start_url[len("https://"):]
                    result["https"]["https_unavailable"] = True
                    resp = await page.goto(start_url, wait_until="domcontentloaded")
                else:
                    raise
            if resp is None:
                raise RuntimeError("Сайт не вернул ответ")
            status = resp.status
            chain = []
            r = resp.request
            while r.redirected_from:
                r = r.redirected_from
                chain.insert(0, r.url)
            result["redirect_chain"] = chain + [page.url]
            result["final_url"] = page.url
            final_host = urlsplit(page.url).hostname or root_host
            if not _same_site(final_host, root_host):
                result["errors"].append({"url": start_url, "error": f"Перенаправление на другой домен: {final_host}"})
            root_host = final_host
            await stage("connect", "done", f"HTTP {status}, {time.monotonic() - t0:.1f} с")
            if status >= 400:
                raise RuntimeError(f"Сайт вернул HTTP {status}")

            # ---------- 2. HTTPS
            await stage("https", "running", "")
            https_info = result["https"]
            https_info.update({"final_scheme": urlsplit(page.url).scheme, "cert_valid": cert_valid})
            try:
                headers = await resp.all_headers()
                https_info["hsts"] = "strict-transport-security" in headers
                result["main_headers"] = headers
            except Exception:
                https_info["hsts"] = False
                result["main_headers"] = {}
            http_url = "http://" + root_host + "/"
            try:
                r_http = await ctx.request.get(http_url, max_redirects=0, timeout=15000, fail_on_status_code=False)
                loc = r_http.headers.get("location", "")
                https_info["http_status"] = r_http.status
                https_info["http_redirects_to_https"] = bool(300 <= r_http.status < 400 and loc.lower().startswith("https://"))
                https_info["http_location"] = loc[:300]
                await r_http.dispose()
            except Exception as e:
                https_info["http_redirects_to_https"] = None
                https_info["http_error"] = str(e)[:200]
            ok = https_info["final_scheme"] == "https" and cert_valid
            await stage("https", "done", "HTTPS, сертификат действителен" if ok else ("HTTPS недоступен" if https_info["final_scheme"] != "https" else "Проблема с сертификатом"))

            # ---------- 3. HTML
            await stage("html", "running", "")
            try:
                result["main_html"] = (await resp.text())[:600000]
            except Exception:
                result["main_html"] = ""
            await stage("html", "done", f"{len(result['main_html']) // 1024} КБ исходного HTML")

            # ---------- 4. DOM
            await stage("dom", "running", "")
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            await page.wait_for_timeout(1500)
            first = await page.evaluate(EXTRACT_JS)
            first.update({"url": page.url, "status": status, "depth": 0})
            result["pages"].append(first)
            await stage("dom", "done", f"{first['counts']['elements']} элементов после выполнения JavaScript")

            # ---------- 5. Обход страниц
            await stage("pages", "running", f"1 из {st.max_pages}")
            seen = {_clean_url(page.url), _clean_url(start_url)}
            queue: list[tuple[int, int, str]] = []  # (priority, depth, url)
            doc_links: set[str] = set()

            def enqueue(links: list[dict], depth: int) -> None:
                for ln in links:
                    href = _clean_url(ln.get("href", ""))
                    if not href.startswith(("http://", "https://")):
                        continue
                    host = urlsplit(href).hostname or ""
                    if not _same_site(host, root_host):
                        continue
                    hint = f"{href} {ln.get('text', '')}"
                    if DOC_EXT_RE.search(href):
                        if PRIORITY_RE.search(hint):
                            doc_links.add(href)
                        continue
                    if href in seen or SKIP_EXT_RE.search(href) or DANGEROUS_RE.search(urlsplit(href).path + "?" + urlsplit(href).query):
                        continue
                    seen.add(href)
                    prio = 0 if PRIORITY_RE.search(hint) else (1 if ln.get("footer") else 2)
                    queue.append((prio, depth, href))
                queue.sort(key=lambda x: (x[0], x[1]))

            enqueue(first["links"], 1)
            while queue and len(result["pages"]) < st.max_pages:
                if time.monotonic() > deadline - st.page_timeout:
                    result["partial"] = True
                    result["errors"].append({"url": "", "error": "Достигнут общий лимит времени обхода"})
                    break
                _, depth, url = queue.pop(0)
                if depth > st.max_depth:
                    continue
                try:
                    r2 = await page.goto(url, wait_until="domcontentloaded")
                    if r2 is None:
                        continue
                    if not _same_site(urlsplit(page.url).hostname or "", root_host):
                        continue
                    if DANGEROUS_RE.search(urlsplit(page.url).path):
                        continue
                    ctype = (await r2.all_headers()).get("content-type", "")
                    if "html" not in ctype:
                        continue
                    try:
                        await page.wait_for_load_state("networkidle", timeout=4000)
                    except Exception:
                        pass
                    data = await page.evaluate(EXTRACT_JS)
                    data.update({"url": page.url, "status": r2.status, "depth": depth})
                    data["inline_scripts"] = data["inline_scripts"][:40000]
                    result["pages"].append(data)
                    if depth < st.max_depth:
                        enqueue(data["links"], depth + 1)
                    await stage("pages", "running", f"{len(result['pages'])} из {st.max_pages}")
                except Exception as e:
                    result["errors"].append({"url": url, "error": str(e).split("\n")[0][:200]})
            await stage("pages", "done", f"Проверено страниц: {len(result['pages'])}")

            # ---------- документы-файлы (PDF и т.п.) и типовые адреса политики — только GET
            for href in list(doc_links)[:6]:
                if time.monotonic() > deadline - 10:
                    break
                result["documents_fetched"].append(await _fetch_document(ctx, href))
            result["_probe_needed"] = True
            result["probes"] = []
            if time.monotonic() < deadline - 15:
                base = f"{urlsplit(page.url).scheme}://{root_host}"
                crawled = {p["url"].rstrip("/") for p in result["pages"]}
                for path in POLICY_PROBES:
                    u = base + path
                    if u.rstrip("/") in crawled:
                        continue
                    try:
                        rp = await ctx.request.get(u, timeout=10000, max_redirects=3, fail_on_status_code=False)
                        body = ""
                        if rp.status == 200 and "html" in rp.headers.get("content-type", ""):
                            body = (await rp.text())[:300000]
                        result["probes"].append({"url": u, "status": rp.status, "final_url": rp.url, "html": body})
                        await rp.dispose()
                    except Exception as e:
                        result["probes"].append({"url": u, "status": 0, "error": str(e)[:120], "html": ""})

            result["cookies"] = await ctx.cookies()

            # ---------- данные для платного модуля безопасности (только безопасные GET)
            if deep and time.monotonic() < deadline - 12:
                from ..secaudit.collect import collect_security, fetch_external_js
                base = f"{urlsplit(page.url).scheme}://{root_host}"
                try:
                    result["security"] = await collect_security(ctx, base, deadline)
                    result["security"]["external_js"] = await fetch_external_js(ctx, result["pages"], root_host, deadline)
                except Exception as e:
                    result["security"] = {"error": str(e)[:200]}

            await ctx.close()
        except Exception as e:
            result["errors"].append({"url": start_url, "error": str(e).split("\n")[0][:300]})
            result["fatal"] = str(e).split("\n")[0][:300]
        finally:
            await browser.close()
            await proxy.stop()
    result["duration_s"] = round(time.monotonic() - started, 1)
    return result


async def _fetch_document(ctx, href: str) -> dict:
    """GET документа (PDF/DOC/TXT) с ограничением размера; извлекает текст PDF для проверки ключевых слов."""
    info = {"url": href, "status": 0, "content_type": "", "size": 0, "text": ""}
    try:
        r = await ctx.request.get(href, timeout=20000, max_redirects=3, fail_on_status_code=False)
        info["status"] = r.status
        info["content_type"] = r.headers.get("content-type", "")
        body = await r.body()
        info["size"] = len(body)
        if r.status == 200 and len(body) <= 8_000_000:
            if body[:4] == b"%PDF":
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(io.BytesIO(body))
                    info["text"] = "\n".join((p.extract_text() or "") for p in reader.pages[:30])[:200000]
                except Exception as e:
                    info["error"] = f"PDF не прочитан: {e}"[:200]
            elif "text" in info["content_type"]:
                info["text"] = body.decode("utf-8", "replace")[:200000]
        await r.dispose()
    except Exception as e:
        info["error"] = str(e)[:200]
    return info


def url_join(base: str, href: str) -> str:
    return urljoin(base, href)
