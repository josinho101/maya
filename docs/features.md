# Features

This document describes every feature of the AI-powered API test automation framework in detail. For a quick orientation, see the [root README](../README.md); for class/sequence diagrams and implementation internals, see [tech.md](tech.md).

## Overview

The app turns an OpenAPI/Swagger specification into a working, self-verifying test suite with minimal human effort. A user uploads a spec, the system generates a broad set of test cases with an LLM, a human reviews and approves them, and the execution engine runs them against a real environment — automatically chaining CREATE/READ/UPDATE/DELETE calls together and verifying that each operation actually had the expected effect. Everything is exposed through a project-based web UI.

## Project Management

Projects are the top-level container for everything else: a Swagger spec, its generations, its executions, its environments. Creating a project just needs a name and an optional description — the app derives a URL-safe slug from the name and uses it to namespace all of that project's files on disk. Project detail views surface counts of generations and executions so a user can see project activity at a glance. Deleting a project removes all of its associated data (uploaded spec, parsed output, generated test cases, and execution history), so it's treated as a destructive, all-or-nothing operation.

## Swagger / OpenAPI Import

A project's test suite starts with importing an API definition, either by uploading a `.yaml`/`.yml`/`.json` file directly or by pointing the app at a URL (or local path) it should fetch and parse. The parser supports both Swagger 2.0 and OpenAPI 3.0 shapes, resolving `$ref` pointers and extracting, per endpoint: path/query/header parameters, request body schema, and response schemas keyed by status code.

A distinctive feature here is **change-aware re-parsing**: every endpoint's parsed details are hashed (SHA-256 over method + path + extracted details), and on a re-upload, endpoints whose hash hasn't changed are reused verbatim instead of being re-parsed. This means re-importing a spec after a small change only affects the endpoints that actually changed, which matters because it also drives which endpoints need their test cases regenerated.

Importing a spec also auto-creates **environments** from the spec's declared servers (see Environment Management below), so the user doesn't have to manually re-enter base URLs that are already in the spec.

## AI-Driven Test Case Generation

This is the core value proposition: instead of a human writing test cases by hand, the app prompts a local LLM (via Ollama) to generate them directly from the parsed API schema. For each endpoint, it generates four categories of test cases:

- **Positive** — happy-path requests that should succeed.
- **Negative** — invalid inputs that should be rejected.
- **Boundary** — edge values (empty strings, zero, max length, etc.).
- **Required-field** — one case per required field, omitting it to confirm the API enforces it.

Generation is resilient to the realities of working with a local LLM: if a single combined prompt gets truncated (hits the model's output token limit) or returns malformed JSON, the generator retries, and if it keeps failing, falls back to generating each category in its own smaller, separate LLM call rather than giving up on the endpoint entirely.

After the raw test cases come back, the generator does meaningful post-processing automatically: it assigns unique IDs per endpoint, normalizes and de-duplicates `lifecycle_role` assignments (only one test case per endpoint can be the canonical "create", "read", "update", or "delete" case — others are demoted to "independent"), backfills missing lifecycle roles where it can infer them, and **synthesizes verification test cases** (`verify_create`, `verify_update`, `verify_delete`) that aren't written by the LLM at all but are added by the framework to check that a create/update/delete actually had its intended effect. Every generated test case starts with `source: "system"` and `needs_review: true`, so nothing reaches execution without a human looking at it first (see Review & Approval below).

## Scenario-Based (Manual) Test Case Generation

Beyond the bulk LLM sweep, a user can describe a specific scenario in plain language ("create a user with a missing email and confirm a 422 is returned") and have the system generate exactly one test case from it, scoped to a chosen endpoint and method. This is useful for covering a case the bulk generator missed, or for testing a specific business rule a human knows about but an LLM reading the schema alone wouldn't infer.

Because this still requires an LLM call, submissions are handled as **asynchronous background jobs**: submitting a scenario queues a job and returns immediately, the job is picked up by a single background worker, and its status (`QUEUED → RUNNING → DONE/FAILED/CANCELLED`) is polled from the UI. A user can attach real files to the scenario (e.g. for file-upload endpoints), which override any placeholder file content the LLM might generate, and can cancel a job at any point — including after it's already running, in which case the result is discarded rather than saved once the LLM call returns. Job state is persisted to disk, so an in-flight job isn't silently lost if the server restarts; queued jobs are re-queued and any job that was actually running gets marked failed.

## Gherkin Step Narration

Once a test case's request/response shape exists (from either generation path), a separate LLM pass turns it into a human-readable Given/When/Then/And narrative. This doesn't change what the test case does — it's a documentation layer that makes a generated, fairly technical JSON structure understandable to someone reviewing it without reading raw payloads. Step generation runs per test case and failures are isolated: if narrating one test case fails, that test case keeps its other data and simply lacks steps, rather than failing the whole batch.

## Review & Approval Workflow

Every test case carries two provenance fields: `source` (`"system"` if the LLM generated it, `"manual"` if a human wrote or edited it) and `needs_review` (whether a human still needs to sign off on it). System-generated test cases start out needing review; manual test cases and anything a human has edited are considered already reviewed.

A user can approve test cases individually or all at once for a generation. A generation only becomes `APPROVED` once every test case in it has `needs_review: false` — and a generation must be in the `APPROVED` state before it can be executed. This gate exists so that nothing the LLM produced runs against a real (possibly stateful, possibly production-adjacent) API without a human having at least glanced at it first.

## CRUD Lifecycle Execution & Self-Healing Verification

This is the framework's most distinctive execution behavior. Rather than firing every test case at the API independently, the execution engine recognizes when a group of test cases for the same resource forms a CRUD lifecycle and runs them as a connected chain:

1. Run the **CREATE** test case and capture the response.
2. Extract the new resource's ID from that response.
3. Run the **READ** test case using the real ID (substituted into the path), then run the **verify_create** check that confirms the read-back data matches what was sent on create.
4. Run **UPDATE** using the real ID, then **verify_update** confirms the change took effect.
5. Run **DELETE** using the real ID, then **verify_delete** confirms the resource is actually gone (expects a 404 on a follow-up read).

Resource data flows between steps via a `{LAST_CREATED_RESOURCE.field}` placeholder syntax that can appear anywhere in a test case's path/query/body parameters, so a test case doesn't need to hardcode an ID it can't know in advance. If the CREATE step fails or no resource ID can be extracted from its response, the dependent verification steps aren't silently skipped from the report — they're explicitly recorded as `SKIPPED` with a reason, so the report always accounts for every test case in the catalog. Any test case that doesn't fit the lifecycle pattern (negative tests, boundary tests, etc.) still runs independently alongside the chain.

This lifecycle-aware execution is effectively a **self-healing verification loop**: it doesn't just check that an endpoint returns the right status code, it checks that the system's actual state changed the way the API claims it did.

## Validation Engine

Each HTTP method has its own validator (GET, POST, PUT, PATCH, DELETE), all sharing a common base of checks: status code matching, required-field presence, and field-type correctness against the expectations declared on the test case. POST/PUT/PATCH validators additionally check that fields sent in the request are echoed back correctly in the response (value match), and the lifecycle verification steps use a dedicated data-consistency check that compares a create/update payload against what a subsequent read returns. Every test case execution ends in one of three states — `PASS`, `FAIL`, or `SKIPPED` — each with a detailed breakdown of which individual checks passed or failed.

## Execution Reporting

Every execution produces both a JSON report (full structured results, useful for tooling) and an HTML report (a readable, browsable summary with pass/fail/skip counts, success rate, and per-test-case expandable detail showing the exact request sent and response received). Reports are kept in two places: a `latest` copy that always reflects the most recent run, and a timestamped copy in `history` so past runs remain available for comparison even after a project has been re-executed many times.

## Environment Management

An environment is just a named base URL a project's test cases can be executed against. Environments come from two sources: **swagger-sourced** environments are auto-created from the `servers` list in the imported spec (and can be renamed but not deleted, since they reflect the spec itself), and **manual** environments are added by hand for cases like a separate staging or local instance not declared in the spec. When triggering an execution, the user picks which environment to run against (defaulting to the first available one), and that environment's URL becomes the base URL for every request in that run.

## Authentication & Roles

The app uses simple username/password login backed by a JWT session token (24-hour expiry by default). There are two roles: **admin**, which can create/modify/delete projects, trigger generation, approve test cases, and trigger execution; and **viewer**, which can read everything (projects, generations, executions, environments) but can't make changes. This is a lightweight model suited to small teams rather than a full multi-tenant permission system.

## Logging

The app maintains three separate log streams: a general application log (business logic, generation/execution lifecycle events, auth), an API request log, and a dedicated LLM log that captures full prompts and responses sent to/from Ollama — useful for debugging why a generation produced unexpected test cases. Logs rotate by size, by time, or by both (whichever threshold is hit first), with a configurable number of backups retained.

## Web UI Walkthrough

- **Projects page** — the landing page after login; lists all projects as cards, with create/edit/delete available to admins, and a live indicator on any project with a generation currently in progress.
- **Project detail page** — a tabbed workspace per project: *Overview* (spec upload/import, summary tiles), *Generations* (list with status and progress, trigger new ones, stop in-progress ones), *Executions* (paginated history with pass/fail summaries and report links), *Scenarios* (manual scenario job submissions and their status), and *Environments* (manage base URLs).
- **Generation review page** — where the bulk of human review work happens: browse all test cases grouped by endpoint, filter to only those needing review, approve individually or in bulk, edit or delete a test case, add a brand-new manual test case (pre-filled with a schema-based sample), submit a scenario job, and finally trigger execution against a chosen environment once the generation is approved.
- **Execution report page** — shows summary statistics, a searchable list of every test case's result with expandable request/response detail and validation breakdowns, a link to the standalone HTML report, and quick access to re-run the same generation.
