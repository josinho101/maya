"""Pydantic v2 schemas for the file-based data model (project, environment, test case,
view snapshot, run summary, healing event) per plan.md §3.4."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter

# --- Project config sub-blocks (F1-010) -------------------------------------------------


class ExplorationConfig(BaseModel):
    """Shared exploration budgets/defaults, overridable per-environment."""

    max_steps: int = 30
    plateau_steps: int = 5

    model_config = {"extra": "allow"}


class HealingConfig(BaseModel):
    auto_apply_threshold: float = 0.90
    vision_fallback_after_attempts: int = 2

    model_config = {"extra": "allow"}


class NotificationsConfig(BaseModel):
    model_config = {"extra": "allow"}


class ConcurrencyConfig(BaseModel):
    model_config = {"extra": "allow"}


class Project(BaseModel):
    id: str
    name: str
    description: str | None = None
    archived: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    test_types: list[Literal["ui", "api"]]
    default_environment: str
    environments: list[str]
    exploration: ExplorationConfig = Field(default_factory=ExplorationConfig)
    healing: HealingConfig = Field(default_factory=HealingConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)


# --- Environment / package sub-blocks (F1-020) -------------------------------------------


class AuthConfig(BaseModel):
    strategy: str
    secure_ref: str
    username_field: LocatorTarget | None = None
    password_field: LocatorTarget | None = None
    submit_button: LocatorTarget | None = None


class UIPackage(BaseModel):
    base_url: str
    auth: AuthConfig | None = None
    env_vars: dict[str, str] = Field(default_factory=dict)
    upload_fixtures: list[str] = Field(default_factory=list)
    instructions: str | None = None


class SpecRef(BaseModel):
    source: Literal["url", "file"]
    value: str
    pinned_version: str | None = None


class APIPackage(BaseModel):
    """Minimal stub — fully fleshed out in F17."""

    spec_ref: SpecRef | None = None
    env_vars: dict[str, str] = Field(default_factory=dict)
    upload_fixtures: list[str] = Field(default_factory=list)
    instructions: str | None = None


class ScheduleConfig(BaseModel):
    cron: str | None = None


class Environment(BaseModel):
    id: str
    label: str
    archived: bool = False
    schedule: ScheduleConfig | None = None
    is_destructive_safe: bool = False
    packages: dict[str, UIPackage | APIPackage] = Field(default_factory=dict)


class EnvironmentImportManifest(BaseModel):
    """Shape of the `environment.json` inside an environment import/sample zip."""

    tag: str
    schedule: ScheduleConfig | None = None
    is_destructive_safe: bool = False
    base_url: str = ""
    auth: AuthConfig | None = None
    env_vars: dict[str, str] = Field(default_factory=dict)


# --- Test case schemas (F1-030) -----------------------------------------------------------


class TestCaseBase(BaseModel):
    id: str = ""
    protocol: str
    status: Literal["pending", "approved", "needs_review", "archived"] = "pending"
    created_by: Literal["exploration_agent", "scenario_interpreter", "api_discovery_agent", "human"]
    source_scenario_ref: str | None = None
    tags: list[str] = Field(default_factory=list)
    healing_history_ref: str | None = None
    last_run_status: str | None = None
    last_execution_time_ms: int | None = None


class LocatorTarget(BaseModel):
    strategy: str
    value: str


class UIStep(BaseModel):
    action: str
    target: LocatorTarget | None = None
    input: Any | None = None
    assertion: Any | None = None
    fixture_ref: str | None = None


class UITestCase(TestCaseBase):
    protocol: Literal["ui"] = "ui"
    view_identity: str
    locator_confidence: float
    steps: list[UIStep] = Field(default_factory=list)


class APITestCase(TestCaseBase):
    """Stub — full API test case shape (operation_ids, steps, etc.) added in F18-060."""

    protocol: Literal["api"] = "api"


TestCase = Annotated[UITestCase | APITestCase, Field(discriminator="protocol")]
TestCaseAdapter: TypeAdapter[UITestCase | APITestCase] = TypeAdapter(TestCase)


# --- View snapshot / run summary / healing log schemas (F1-040) --------------------------


class ViewSnapshotElement(BaseModel):
    ref: str
    role: str | None = None
    name: str | None = None
    data_testid: str | None = Field(default=None, alias="data-testid")
    path_fingerprint: str | None = None

    model_config = {"populate_by_name": True}


class ViewDiff(BaseModel):
    severity: Literal["none", "cosmetic", "structural-minor", "structural-major"]
    added: list[Any] = Field(default_factory=list)
    removed: list[Any] = Field(default_factory=list)
    changed: list[Any] = Field(default_factory=list)


class ViewSnapshotRecord(BaseModel):
    view_identity: str
    captured_at: datetime
    page_hash: str
    screenshot_ref: str | None = None
    elements: list[ViewSnapshotElement] = Field(default_factory=list)
    diff_against_previous: ViewDiff | None = None


class RunResultEntry(BaseModel):
    test_case_id: str
    status: str
    healed_pass: bool = False
    execution_time_ms: int
    healing_event_refs: list[str] = Field(default_factory=list)
    screenshot_refs: list[str] = Field(default_factory=list)
    mapping_refs: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    run_id: str
    environment_id: str
    trigger: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    total_job_time_ms: int
    results: list[RunResultEntry] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class HealingCandidate(BaseModel):
    strategy: str
    value: str
    confidence: float
    signal_breakdown: dict[str, float] = Field(default_factory=dict)


class HealingEventLogEntry(BaseModel):
    heal_id: str
    run_id: str
    step_id: str
    failure_type: str
    original_locator: dict[str, Any] | None = None
    original_mapping: dict[str, Any] | None = None
    candidates: list[HealingCandidate] = Field(default_factory=list)
    applied: HealingCandidate | None = None
    auto_applied: bool = False
    escalated_to_vision: bool = False
    escalated_to_llm: bool = False
