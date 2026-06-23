import json

from maya.storage.models import (
    APITestCase,
    Environment,
    HealingCandidate,
    HealingEventLogEntry,
    Project,
    RunResultEntry,
    RunSummary,
    TestCaseAdapter,
    UITestCase,
    ViewDiff,
    ViewSnapshotRecord,
)

PROJECT_JSON = {
    "id": "acme-webapp",
    "name": "Acme Webapp",
    "description": None,
    "archived": False,
    "test_types": ["ui", "api"],
    "default_environment": "staging",
    "environments": ["dev", "staging", "prod"],
    "exploration": {"budget": "shared defaults, overridable per-environment"},
    "healing": {"auto_apply_threshold": 0.90, "vision_fallback_after_attempts": 2},
    "notifications": {"on_failure": "slack"},
    "concurrency": {"max_parallel_jobs": 4},
}

ENVIRONMENT_JSON = {
    "id": "staging",
    "label": "Staging",
    "archived": False,
    "schedule": {"cron": "0 */6 * * *"},
    "is_destructive_safe": True,
    "packages": {
        "ui": {
            "base_url": "https://staging.acme.com",
            "auth": {"strategy": "form_login", "secure_ref": "acme-webapp.staging"},
            "env_vars": {"FEATURE_FLAG_X": "true"},
            "upload_fixtures": ["builtin:sample.pdf", "builtin:sample.png"],
            "instructions": None,
        },
        "api": {
            "spec_ref": {
                "source": "url",
                "value": "https://api-staging.acme.com/openapi.json",
                "pinned_version": "v2.3.1",
            },
            "env_vars": {"API_KEY": "${secure.acme-webapp.staging.api_key}"},
            "upload_fixtures": ["builtin:sample.csv"],
            "instructions": "Treat /internal/* endpoints as out of scope.",
        },
    },
}


def test_project_round_trip():
    project = Project.model_validate(PROJECT_JSON)
    assert project.model_dump(mode="json") == PROJECT_JSON


def test_environment_parses_plan_example():
    env = Environment.model_validate(ENVIRONMENT_JSON)

    assert env.id == "staging"
    assert env.label == "Staging"
    assert env.schedule.cron == "0 */6 * * *"
    assert env.is_destructive_safe is True

    ui = env.packages["ui"]
    assert ui.base_url == "https://staging.acme.com"
    assert ui.auth.strategy == "form_login"
    assert ui.auth.secure_ref == "acme-webapp.staging"
    assert ui.env_vars == {"FEATURE_FLAG_X": "true"}
    assert ui.upload_fixtures == ["builtin:sample.pdf", "builtin:sample.png"]
    assert ui.instructions is None

    api = env.packages["api"]
    assert api.spec_ref.source == "url"
    assert api.spec_ref.value == "https://api-staging.acme.com/openapi.json"
    assert api.spec_ref.pinned_version == "v2.3.1"
    assert api.env_vars == {"API_KEY": "${secure.acme-webapp.staging.api_key}"}
    assert api.upload_fixtures == ["builtin:sample.csv"]
    assert api.instructions == "Treat /internal/* endpoints as out of scope."


def test_ui_test_case_discriminated_union_resolves():
    data = {
        "id": "tc_1",
        "protocol": "ui",
        "status": "pending",
        "created_by": "exploration_agent",
        "tags": ["smoke"],
        "view_identity": "login-page",
        "locator_confidence": 0.95,
        "steps": [
            {
                "action": "click",
                "target": {"strategy": "data-testid", "value": "submit-button"},
            }
        ],
    }
    result = TestCaseAdapter.validate_json(json.dumps(data))
    assert isinstance(result, UITestCase)
    assert result.view_identity == "login-page"
    assert result.steps[0].target.value == "submit-button"


def test_api_test_case_stub_discriminated_union_resolves():
    data = {
        "id": "tc_2",
        "protocol": "api",
        "status": "pending",
        "created_by": "api_discovery_agent",
        "tags": [],
    }
    result = TestCaseAdapter.validate_json(json.dumps(data))
    assert isinstance(result, APITestCase)
    assert result.protocol == "api"


def test_view_snapshot_record_round_trip():
    data = {
        "view_identity": "login-page",
        "captured_at": "2026-06-23T10:00:00Z",
        "page_hash": "abc123",
        "screenshot_ref": "shots/login.png",
        "elements": [
            {
                "ref": "el-1",
                "role": "button",
                "name": "Submit",
                "data-testid": "submit-button",
                "path_fingerprint": "fp-1",
            }
        ],
        "diff_against_previous": {
            "severity": "cosmetic",
            "added": [],
            "removed": [],
            "changed": ["color"],
        },
    }
    record = ViewSnapshotRecord.model_validate(data)
    assert record.elements[0].data_testid == "submit-button"
    assert record.diff_against_previous.severity == "cosmetic"

    dumped = record.model_dump(mode="json", by_alias=True)
    assert dumped["elements"][0]["data-testid"] == "submit-button"


def test_run_summary_round_trip():
    data = {
        "run_id": "run_1",
        "environment_id": "staging",
        "trigger": {"type": "cron"},
        "decision": {"login-page": "replay"},
        "total_job_time_ms": 5000,
        "results": [
            {
                "test_case_id": "tc_1",
                "status": "passed",
                "healed_pass": False,
                "execution_time_ms": 412,
                "healing_event_refs": [],
                "screenshot_refs": ["shots/tc_1.png"],
                "mapping_refs": [],
            }
        ],
        "summary": {"passed": 1, "failed": 0},
    }
    summary = RunSummary.model_validate(data)
    assert summary.model_dump(mode="json") == data
    assert isinstance(summary.results[0], RunResultEntry)


def test_healing_event_log_entry_round_trip_ui_locator():
    data = {
        "heal_id": "heal_1",
        "run_id": "run_1",
        "step_id": "s1",
        "failure_type": "locator_not_found",
        "original_locator": {"strategy": "data-testid", "value": "old-id"},
        "original_mapping": None,
        "candidates": [
            {
                "strategy": "aria-label",
                "value": "Submit",
                "confidence": 0.92,
                "signal_breakdown": {"text_similarity": 0.9},
            }
        ],
        "applied": {
            "strategy": "aria-label",
            "value": "Submit",
            "confidence": 0.92,
            "signal_breakdown": {"text_similarity": 0.9},
        },
        "auto_applied": True,
        "escalated_to_vision": False,
        "escalated_to_llm": False,
    }
    entry = HealingEventLogEntry.model_validate(data)
    assert entry.model_dump(mode="json") == data
    assert isinstance(entry.applied, HealingCandidate)


def test_healing_event_log_entry_round_trip_api_mapping():
    data = {
        "heal_id": "heal_2",
        "run_id": "run_2",
        "step_id": "s2",
        "failure_type": "field_not_found",
        "original_locator": None,
        "original_mapping": {"operation_id": "createOrder", "field": "qty"},
        "candidates": [],
        "applied": None,
        "auto_applied": False,
        "escalated_to_vision": False,
        "escalated_to_llm": True,
    }
    entry = HealingEventLogEntry.model_validate(data)
    assert entry.model_dump(mode="json") == data


def test_view_diff_model():
    diff = ViewDiff.model_validate({"severity": "none", "added": [], "removed": [], "changed": []})
    assert diff.severity == "none"
