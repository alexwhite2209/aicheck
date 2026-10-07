"""Локальный egress-прокси для браузера краулера.

Chromium настроен ходить в сеть только через этот прокси. Прокси:
  * резолвит имя сам и подключается только к проверенному публичному IP (защита от DNS rebinding);
  * пропускает только порты 80/443;
  * для обычного HTTP разрешает только GET/HEAD/OPTIONS;
  * считает заблокированные попытки (попадают в отчёт).
Методы внутри HTTPS-туннеля дополнительно фильтруются в браузере (route-обработчик в browser.py).
"""
import asyncio
import contextlib
import logging
from urllib.parse import urlsplit

from .ssrf import UnsafeURLError, is_ip_allowed, resolve_public

log = logging.getLogger(__name__)
SAFE_HTTP_METHODS = {b"GET", b"HEAD", b"OPTIONS"}
MAX_HEADER = 64 * 1024


class EgressProxy:
    def __init__(self, test_allowlist: set[str] | None = None, connect_timeout: float = 15.0):
        self.server: asyncio.base_events.Server | None = None
        self.port = 0
        self.blocked: list[dict] = []
        self.test_allowlist = test_allowlist or set()
        self.connect_timeout = connect_timeout
        self._tasks: set[asyncio.Task] = set()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self.server.wait_closed(), 2)
        for t in list(self._tasks):
            t.cancel()

    def _block(self, host: str, port: int, reason: str) -> None:
        if len(self.blocked) < 200:
            self.blocked.append({"host": host, "port": port, "reason": reason})

    async def _resolve(self, host: str, port: int) -> str:
        if f"{host}:{port}" in self.test_allowlist:
            return host
        if port not in (80, 443):
            raise UnsafeURLError("Нестандартный порт")
        loop = asyncio.get_running_loop()
        ips = await loop.run_in_executor(None, resolve_public, host, port)
        ip = ips[0]
        if not is_ip_allowed(ip):  # повторная проверка конкретного адреса подключения
            raise UnsafeURLError("Внутренний адрес")
        return ip

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        if task:
            self._tasks.add(task)
        try:
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 30)
        except Exception:
            writer.close()
            return
        try:
            if len(head) > MAX_HEADER:
                raise UnsafeURLError("Слишком большой заголовок")
            request_line, _, rest = head.partition(b"\r\n")
            method, target, version = request_line.split(b" ", 2)
            if method == b"CONNECT":
                host, _, port_s = target.decode("latin-1").rpartition(":")
                host = host.strip("[]").lower()
                port = int(port_s or 443)
                ip = await self._resolve(host, port)
                up_r, up_w = await asyncio.wait_for(asyncio.open_connection(ip, port), self.connect_timeout)
                writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                await writer.drain()
                await self._pipe(reader, writer, up_r, up_w)
                return
            if method not in SAFE_HTTP_METHODS:
                parts = urlsplit(target.decode("latin-1"))
                self._block(parts.hostname or "", parts.port or 80, f"метод {method.decode()} запрещён")
                writer.write(b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                await writer.drain()
                writer.close()
                return
            parts = urlsplit(target.decode("latin-1"))
            if parts.scheme != "http" or not parts.hostname:
                raise UnsafeURLError("Некорректный запрос")
            host, port = parts.hostname.lower(), parts.port or 80
            ip = await self._resolve(host, port)
            up_r, up_w = await asyncio.wait_for(asyncio.open_connection(ip, port), self.connect_timeout)
            path = parts.path or "/"
            if parts.query:
                path += "?" + parts.query
            headers = [h for h in rest.split(b"\r\n") if h and not h.lower().startswith((b"proxy-", b"connection:", b"keep-alive:"))]
            up_w.write(method + b" " + path.encode("latin-1") + b" " + version + b"\r\n" + b"\r\n".join(headers)
                       + b"\r\nConnection: close\r\n\r\n")
            await up_w.drain()
            await self._pipe(reader, writer, up_r, up_w)
        except (UnsafeURLError, ValueError) as e:
            try:
                host = target.decode("latin-1")  # type: ignore[possibly-undefined]
            except Exception:
                host = "?"
            self._block(host, 0, str(e))
            with contextlib.suppress(Exception):
                writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                await writer.drain()
            writer.close()
        except Exception as e:  # сетевые ошибки
            log.debug("proxy error: %s", e)
            with contextlib.suppress(Exception):
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                await writer.drain()
            writer.close()
        finally:
            if task:
                self._tasks.discard(task)

    @staticmethod
    async def _pipe(cr: asyncio.StreamReader, cw: asyncio.StreamWriter, ur: asyncio.StreamReader, uw: asyncio.StreamWriter) -> None:
        async def copy(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
            try:
                while True:
                    data = await src.read(65536)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
            except Exception:
                pass
            finally:
                with contextlib.suppress(Exception):
                    dst.close()

        await asyncio.gather(copy(cr, uw), copy(ur, cw))
