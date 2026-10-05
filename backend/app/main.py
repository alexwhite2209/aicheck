import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import admin, audit, auth, payments, public, report, user
from .config import get_settings
from .db import Base, SessionLocal, engine
from .legal.seed import seed_all
from .security import csrf_ok

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_all(db)
    yield


app = FastAPI(title="Норма — AI-аудит сайтов по законодательству РФ", version="1.0.0", lifespan=lifespan,
              docs_url=None if settings.is_prod else "/api/docs", redoc_url=None, openapi_url=None if settings.is_prod else "/api/openapi.json")

if settings.cors_list:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"])


@app.middleware("http")
async def security_mw(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.url.path != "/api/payments/webhook" and not csrf_ok(request):
        return JSONResponse({"detail": "CSRF-проверка не пройдена. Обновите страницу."}, status_code=403)
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > 256 * 1024:
        return JSONResponse({"detail": "Слишком большой запрос"}, status_code=413)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/docs"):
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        response.headers.setdefault("Cache-Control", "no-store")
    if settings.is_prod:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    msg = first.get("msg", "Некорректные данные")
    return JSONResponse({"detail": msg.replace("Value error, ", "")}, status_code=422)


@app.get("/api/health")
def health():
    return {"ok": True}


for r in (audit.router, auth.router, user.router, report.router, admin.router, payments.router, public.router):
    app.include_router(r)
