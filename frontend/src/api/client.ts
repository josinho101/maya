const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:9091";

export interface HealthResponse {
  status: string;
}

export type TestType = "ui" | "api";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  archived: boolean;
  created_at: string;
  test_types: TestType[];
  default_environment: string;
  environments: string[];
}

export interface ScheduleConfig {
  cron: string | null;
}

export interface AuthConfig {
  strategy: string;
  secure_ref: string;
}

export interface UIPackage {
  base_url: string;
  auth: AuthConfig | null;
  env_vars: Record<string, string>;
  upload_fixtures: string[];
}

export interface Environment {
  id: string;
  label: string;
  archived: boolean;
  schedule: ScheduleConfig | null;
  is_destructive_safe: boolean;
  packages: Record<string, UIPackage | Record<string, unknown>>;
}

export interface CreateProjectInput {
  name: string;
  description?: string | null;
  test_types: TestType[];
  default_environment?: string;
}

export interface UpdateProjectInput {
  name?: string;
  description?: string | null;
  test_types?: TestType[];
}

export interface AddEnvironmentInput {
  tag: string;
  schedule?: ScheduleConfig | null;
  is_destructive_safe?: boolean;
}

export interface UpdateEnvironmentInput {
  label?: string;
  schedule?: ScheduleConfig | null;
  is_destructive_safe?: boolean;
}

export type UpdatePackageInput = Partial<UIPackage>;

export interface EnvironmentImportManifest {
  tag: string;
  schedule: ScheduleConfig | null;
  is_destructive_safe: boolean;
  base_url: string;
  auth: AuthConfig | null;
  env_vars: Record<string, string>;
}

export type TestCaseStatus = "pending" | "approved" | "needs_review" | "archived";

export interface LocatorTarget {
  strategy: string;
  value: string;
}

export interface UIStep {
  action: string;
  target: LocatorTarget | null;
  input: unknown | null;
  assertion: unknown | null;
  fixture_ref: string | null;
}

interface TestCaseCommon {
  id: string;
  status: TestCaseStatus;
  rejection_reason: string | null;
  created_by: "exploration_agent" | "scenario_interpreter" | "api_discovery_agent" | "human";
  source_scenario_ref: string | null;
  tags: string[];
  healing_history_ref: string | null;
  last_run_status: string | null;
  last_execution_time_ms: number | null;
}

export interface UITestCase extends TestCaseCommon {
  protocol: "ui";
  view_identity: string;
  locator_confidence: number;
  steps: UIStep[];
}

export interface APITestCase extends TestCaseCommon {
  protocol: "api";
}

export type TestCase = UITestCase | APITestCase;

export interface RunResultEntry {
  test_case_id: string;
  status: string;
  healed_pass: boolean;
  execution_time_ms: number;
  healing_event_refs: string[];
  screenshot_refs: string[];
  mapping_refs: string[];
}

export interface RunSummary {
  run_id: string;
  environment_id: string;
  trigger: Record<string, unknown>;
  decision: Record<string, unknown>;
  total_job_time_ms: number;
  results: RunResultEntry[];
  summary: Record<string, number>;
}

export interface HealingCandidate {
  strategy: string;
  value: string;
  confidence: number;
  signal_breakdown: Record<string, number>;
}

export interface HealingEventLogEntry {
  heal_id: string;
  run_id: string;
  step_id: string;
  failure_type: string;
  original_locator: LocatorTarget | null;
  original_mapping: Record<string, unknown> | null;
  candidates: HealingCandidate[];
  applied: HealingCandidate | null;
  auto_applied: boolean;
  escalated_to_vision: boolean;
  escalated_to_llm: boolean;
  resolution: "accepted" | "rejected" | null;
}

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(status: number, detail?: string) {
    super(detail ?? `Request failed: ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

const JSON_HEADERS = { "Content-Type": "application/json" };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, init);
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = await response.json();
      detail = body?.detail;
    } catch {
      detail = undefined;
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const apiClient = {
  getHealth: () => request<HealthResponse>("/health"),

  listProjects: () => request<Project[]>("/api/v1/projects"),

  getProject: (id: string) => request<Project>(`/api/v1/projects/${id}`),

  createProject: (body: CreateProjectInput) =>
    request<Project>("/api/v1/projects", {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),

  updateProject: (id: string, body: UpdateProjectInput) =>
    request<Project>(`/api/v1/projects/${id}`, {
      method: "PUT",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),

  deleteProject: (id: string) => request<void>(`/api/v1/projects/${id}`, { method: "DELETE" }),

  archiveProject: (id: string) =>
    request<Project>(`/api/v1/projects/${id}/archive`, { method: "POST" }),

  listEnvironments: (projectId: string) =>
    request<Environment[]>(`/api/v1/projects/${projectId}/environments`),

  addEnvironment: (projectId: string, body: AddEnvironmentInput) =>
    request<Environment>(`/api/v1/projects/${projectId}/environments`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),

  getEnvironment: (projectId: string, envId: string) =>
    request<Environment>(`/api/v1/projects/${projectId}/environments/${envId}`),

  deleteEnvironment: (projectId: string, envId: string) =>
    request<void>(`/api/v1/projects/${projectId}/environments/${envId}`, { method: "DELETE" }),

  archiveEnvironment: (projectId: string, envId: string) =>
    request<Environment>(`/api/v1/projects/${projectId}/environments/${envId}/archive`, {
      method: "POST",
    }),

  updateEnvironment: (projectId: string, envId: string, body: UpdateEnvironmentInput) =>
    request<Environment>(`/api/v1/projects/${projectId}/environments/${envId}`, {
      method: "PUT",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
    }),

  updatePackage: (projectId: string, envId: string, testType: string, body: UpdatePackageInput) =>
    request<Environment>(
      `/api/v1/projects/${projectId}/environments/${envId}/packages/${testType}`,
      { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify(body) },
    ),

  listTestCases: (projectId: string, status: TestCaseStatus, protocol?: TestType) => {
    const params = new URLSearchParams({ status });
    if (protocol) params.set("protocol", protocol);
    return request<TestCase[]>(`/api/v1/projects/${projectId}/test-cases?${params.toString()}`);
  },

  approveTestCase: (projectId: string, testCaseId: string) =>
    request<TestCase>(`/api/v1/projects/${projectId}/test-cases/${testCaseId}/approve`, {
      method: "POST",
    }),

  rejectTestCase: (projectId: string, testCaseId: string, reason: string) =>
    request<TestCase>(`/api/v1/projects/${projectId}/test-cases/${testCaseId}/reject`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ reason }),
    }),

  patchTestCaseSteps: (projectId: string, testCaseId: string, steps: UIStep[]) =>
    request<TestCase>(`/api/v1/projects/${projectId}/test-cases/${testCaseId}`, {
      method: "PATCH",
      headers: JSON_HEADERS,
      body: JSON.stringify({ steps }),
    }),

  triggerRun: (projectId: string, environmentId: string) =>
    request<RunSummary>(
      `/api/v1/projects/${projectId}/runs?${new URLSearchParams({ environment: environmentId }).toString()}`,
      { method: "POST" },
    ),

  getRun: (runId: string) => request<RunSummary>(`/api/v1/runs/${runId}`),

  getHealingLog: (projectId: string, testCaseId: string) =>
    request<HealingEventLogEntry[]>(`/api/v1/projects/${projectId}/test-cases/${testCaseId}/healing-log`),

  resolveHealing: (healId: string, action: "accept" | "reject") =>
    request<HealingEventLogEntry>(`/api/v1/healing/${healId}/resolve`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ action }),
    }),

  getScreenshotUrl: (runId: string, filename: string) =>
    `${BASE_URL}/api/v1/runs/${runId}/screenshots/${filename}`,

  downloadEnvironmentSampleJson: async (): Promise<Blob> => {
    const response = await fetch(`${BASE_URL}/api/v1/projects/environments/sample-json`);
    if (!response.ok) throw new ApiError(response.status);
    return response.blob();
  },

  parseEnvironmentJson: async (file: File): Promise<EnvironmentImportManifest> => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${BASE_URL}/api/v1/projects/environments/parse-json`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      let detail: string | undefined;
      try {
        detail = (await response.json())?.detail;
      } catch {
        detail = undefined;
      }
      throw new ApiError(response.status, detail);
    }
    return response.json() as Promise<EnvironmentImportManifest>;
  },
};
