"""Ограничение частоты: скользящее окно в памяти или в Redis (если задан REDIS_URL)."""
import threading
import time
from collections import defaultdict, deque

from .config import get_settings


class RateLimiter:
    def __init__(self) -> None:
        self._mem: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._redis = None
        url = get_settings().redis_url
        if url:
            try:
                import redis
                self._redis = redis.Redis.from_url(url, socket_timeout=2)
                self._redis.ping()
            except Exception:
                self._redis = None

    def hit(self, key: str, limit: int, window_s: int) -> tuple[bool, int]:
        """Регистрирует попытку. Возвращает (разрешено, секунд до сброса)."""
        now = time.time()
        if self._redis is not None:
            try:
                rk = f"rl:{key}:{window_s}"
                pipe = self._redis.pipeline()
                pipe.zremrangebyscore(rk, 0, now - window_s)
                pipe.zcard(rk)
                _, count = pipe.execute()
                if count >= limit:
                    oldest = self._redis.zrange(rk, 0, 0, withscores=True)
                    retry = int(window_s - (now - oldest[0][1])) if oldest else window_s
                    return False, max(retry, 1)
                pipe = self._redis.pipeline()
                pipe.zadd(rk, {f"{now}:{id(pipe)}": now})
                pipe.expire(rk, window_s)
                pipe.execute()
                return True, 0
            except Exception:
                pass
        with self._lock:
            q = self._mem[f"{key}:{window_s}"]
            while q and q[0] <= now - window_s:
                q.popleft()
            if len(q) >= limit:
                return False, max(int(window_s - (now - q[0])), 1)
            q.append(now)
            return True, 0


limiter = RateLimiter()
