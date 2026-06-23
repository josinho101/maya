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
  instructions: string | null;
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

export type UpdatePackageInput = Partial<UIPackage>;

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

  updatePackage: (projectId: string, envId: string, testType: string, body: UpdatePackageInput) =>
    request<Environment>(
      `/api/v1/projects/${projectId}/environments/${envId}/packages/${testType}`,
      { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify(body) },
    ),
};
