from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from maya.api.routers import health, projects, test_cases
from maya.logging_setup import configure_logging
from maya.managers.project_manager import (
    ArchivedError,
    EnvironmentAlreadyExistsError,
    EnvironmentNotFoundError,
    EnvironmentTagAlreadyExistsError,
    InvalidSlugError,
    ProjectAlreadyExistsError,
    ProjectManager,
    ProjectNameAlreadyExistsError,
    ProjectNotFoundError,
)
from maya.managers.slugify import EmptySlugError
from maya.startup_checks import check_secure_config_not_tracked
from maya.storage.test_case_store import TestCaseNotFoundError, TestCaseStatusConflictError

FRAMEWORK_DATA_DIR = Path("framework-data")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(FRAMEWORK_DATA_DIR)
    check_secure_config_not_tracked(FRAMEWORK_DATA_DIR / "config" / "secure")
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

app.state.project_manager = ProjectManager(FRAMEWORK_DATA_DIR)


@app.exception_handler(ProjectNotFoundError)
@app.exception_handler(EnvironmentNotFoundError)
def _handle_not_found(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(TestCaseNotFoundError)
def _handle_test_case_not_found(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ProjectAlreadyExistsError)
@app.exception_handler(EnvironmentAlreadyExistsError)
@app.exception_handler(ProjectNameAlreadyExistsError)
@app.exception_handler(EnvironmentTagAlreadyExistsError)
@app.exception_handler(ArchivedError)
@app.exception_handler(TestCaseStatusConflictError)
def _handle_conflict(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidSlugError)
@app.exception_handler(EmptySlugError)
def _handle_invalid(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


app.include_router(health.router)
app.include_router(projects.router)
app.include_router(test_cases.router)
