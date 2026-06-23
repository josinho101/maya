from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from maya.api.routers import health
from maya.logging_setup import configure_logging

FRAMEWORK_DATA_DIR = Path("framework-data")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(FRAMEWORK_DATA_DIR)
    yield


app = FastAPI(
    title="MAYA API",
    description="AI-driven test automation framework — REST API.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Local dev: React dashboard runs on a different origin/port (9090) than this
# API (9091), so the browser needs explicit CORS allowance to read responses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9090"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
