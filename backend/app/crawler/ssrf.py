"""Защита от SSRF: проверка URL и IP-адресов назначения.

Краулер обращается к сети только через egress-прокси (egress_proxy.py), который сам резолвит имя,
проверяет каждый IP этой функцией и подключается к уже проверенному адресу (защита от DNS rebinding).
"""
import ipaddress
import re
import socket
from urllib.parse import urlsplit, urlunsplit

import idna

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {None, 80, 443}
BLOCKED_HOST_SUFFIXES = (".localhost", ".local", ".internal", ".intranet", ".lan", ".home", ".corp",
                         ".arpa", ".localdomain", ".test", ".invalid", ".example")
BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata", "instance-data"}

# Явные диапазоны из ТЗ + прочие служебные сети (ipaddress закрывает и остальное через is_global)
_EXTRA_BLOCKED = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12",
    "192.0.0.0/24", "192.0.2.0/24", "192.88.99.0/24", "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24",
    "203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4", "255.255.255.255/32",
    "::/128", "::1/128", "64:ff9b::/96", "100::/64", "2001:db8::/32", "fc00::/7", "fe80::/10", "ff00::/8",
)]


class UnsafeURLError(ValueError):
    pass


def is_ip_allowed(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped:
            return is_ip_allowed(str(addr.ipv4_mapped))
        if addr.sixtofour:
            return is_ip_allowed(str(addr.sixtofour))
        if addr.teredo:
            return False
    if any(addr in net for net in _EXTRA_BLOCKED):
        return False
    return addr.is_global and not (addr.is_private or addr.is_loopback or addr.is_link_local
                                   or addr.is_multicast or addr.is_reserved or addr.is_unspecified)


def _normalize_host(host: str) -> str:
    host = host.strip().rstrip(".").lower()
    if not host:
        raise UnsafeURLError("Не указан домен")
    try:
        ipaddress.ip_address(host.strip("[]"))
        return host.strip("[]")
    except ValueError:
        pass
    try:
        return idna.encode(host, uts46=True).decode("ascii")
    except idna.IDNAError as e:
        raise UnsafeURLError("Некорректное доменное имя") from e


def host_is_blocked_by_name(host: str) -> bool:
    if host in BLOCKED_HOSTS or host.endswith(BLOCKED_HOST_SUFFIXES):
        return True
    # десятичная/шестнадцатеричная запись IP вида 2130706433 или 0x7f000001
    if re.fullmatch(r"(0x[0-9a-f]+|\d+)", host):
        return True
    if "." not in host and ":" not in host:
        return True
    return False


def normalize_url(raw: str, allowlist: set[str] | None = None) -> str:
    """Нормализует пользовательский ввод в абсолютный http(s) URL и проверяет синтаксис.

    allowlist — только для локальных тестов (host:port), в production не передаётся.
    """
    if allowlist:
        p = urlsplit(raw if "://" in raw else "http://" + raw)
        if p.hostname and f"{p.hostname}:{p.port or 80}" in allowlist:
            return urlunsplit((p.scheme, p.netloc, p.path or "/", p.query, ""))
    raw = (raw or "").strip()
    if len(raw) > 2048:
        raise UnsafeURLError("Слишком длинный URL")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = "https://" + raw
    parts = urlsplit(raw)
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UnsafeURLError("Поддерживаются только адреса http:// и https://")
    if parts.username or parts.password:
        raise UnsafeURLError("URL не должен содержать логин и пароль")
    try:
        port = parts.port
    except ValueError as e:
        raise UnsafeURLError("Некорректный порт") from e
    if port not in ALLOWED_PORTS:
        raise UnsafeURLError("Разрешены только стандартные порты 80 и 443")
    host = _normalize_host(parts.hostname or "")
    if host_is_blocked_by_name(host):
        raise UnsafeURLError("Адрес относится к внутренней или служебной сети")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if not is_ip_allowed(str(ip)):
            raise UnsafeURLError("Адрес относится к внутренней или служебной сети")
        netloc = f"[{host}]" if ip.version == 6 else host
    else:
        netloc = host
    if port:
        netloc = f"{netloc}:{port}"
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def resolve_public(host: str, port: int = 443) -> list[str]:
    """Резолвит имя и возвращает только публичные адреса. Если хоть один адрес внутренний — отказ."""
    host = _normalize_host(host)
    if host_is_blocked_by_name(host):
        raise UnsafeURLError("Адрес относится к внутренней или служебной сети")
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise UnsafeURLError("Домен не найден (DNS)") from e
    ips = sorted({i[4][0] for i in infos})
    if not ips:
        raise UnsafeURLError("Домен не найден (DNS)")
    bad = [ip for ip in ips if not is_ip_allowed(ip)]
    if bad:
        raise UnsafeURLError("Домен указывает на внутренний или служебный адрес")
    return ips


def validate_target(raw: str, allowlist: set[str] | None = None) -> str:
    """Полная проверка адреса, введённого пользователем: синтаксис + DNS."""
    url = normalize_url(raw, allowlist)
    parts = urlsplit(url)
    if allowlist and f"{parts.hostname}:{parts.port or 80}" in allowlist:
        return url
    resolve_public(parts.hostname or "", parts.port or (443 if parts.scheme == "https" else 80))
    return url
