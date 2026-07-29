from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import get_settings
from app.database import engine
from app.errors import AppError
from app.logging_setup import setup_logging
from app.providers.anthropic_llm import AnthropicLLMProvider
from app.providers.llm import set_llm_provider

settings = get_settings()
setup_logging(
    level=settings.log_level,
    log_dir=settings.log_dir or None,
    backup_count=settings.log_backup_count,
)

logger = logging.getLogger("app")
API_V1_STR = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.anthropic_api_key:
        set_llm_provider(
            AnthropicLLMProvider(
                api_key=settings.anthropic_api_key,
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                prompt_cache=settings.llm_prompt_cache,
                prompt_cache_ttl=settings.llm_prompt_cache_ttl,
            )
        )
        logger.info(
            "LLM provider configured: Anthropic model=%s cache=%s ttl=%s",
            settings.llm_model,
            settings.llm_prompt_cache,
            settings.llm_prompt_cache_ttl,
        )
    else:
        logger.warning(
            "ANTHROPIC_API_KEY not set; LLM endpoints return 501"
        )
    if settings.log_dir:
        logger.info(
            "File logging enabled: dir=%s backup_days=%s",
            settings.log_dir,
            settings.log_backup_count,
        )
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="Facio MVP client-service API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=f"{API_V1_STR}/docs",
    redoc_url=f"{API_V1_STR}/redoc",
    openapi_url=f"{API_V1_STR}/openapi.json",
)

cors_origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
] or ["*"]
# Browser forbids Allow-Credentials with wildcard origins.
allow_credentials = cors_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=API_V1_STR)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.url.path != "/health":
        logger.info(
            "%s %s → %s",
            request.method,
            request.url.path,
            response.status_code,
        )
    return response


@app.get("/health")
async def health_check():
    return {"status": "ok"}
