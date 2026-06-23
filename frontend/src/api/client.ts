const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:9091";

export interface HealthResponse {
  status: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new Error(`Request to ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const apiClient = {
  getHealth: () => request<HealthResponse>("/health"),
};
