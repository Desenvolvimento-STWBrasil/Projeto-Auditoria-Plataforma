from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.logging import configure_logging

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.session import engine

from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.api.health import router as health_router

limiter = Limiter(key_func=get_remote_address)

configure_logging(is_debug=settings.IS_DEBUG)


@asynccontextmanager
async def lifespan(_app: FastAPI):

    engine.dispose()

    # Futura: conexão com banco, filas, etc
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    debug=settings.IS_DEBUG,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)

app.include_router(v1_router, prefix=settings.API_PREFIX_V1)
app.include_router(health_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": settings.PROJECT_NAME, "docs": "/docs"}
