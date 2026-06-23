from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from maya.api.routers import health

app = FastAPI(
    title="MAYA API",
    description="AI-driven test automation framework — REST API.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
