import axios from "axios";

const api = axios.create({ baseURL: "/api" });

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("maya_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401, clear session and redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("maya_token");
      localStorage.removeItem("maya_user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;

// Projects
export const getProjects = () => api.get("/projects").then((r) => r.data);
export const createProject = (data) => api.post("/projects", data).then((r) => r.data);
export const getProject = (id) => api.get(`/projects/${id}`).then((r) => r.data);
export const updateProject = (id, data) => api.put(`/projects/${id}`, data).then((r) => r.data);
export const deleteProject = (id) => api.delete(`/projects/${id}`).then((r) => r.data);

// Swagger
export const uploadSwagger = (id, file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post(`/projects/${id}/swagger`, form).then((r) => r.data);
};
export const getSwagger = (id) => api.get(`/projects/${id}/swagger`).then((r) => r.data);
export const importSwaggerFromUrl = (id, url) =>
  api.post(`/projects/${id}/swagger/url`, { url }).then((r) => r.data);

// Generations
export const triggerGeneration = (id, body = {}) =>
  api.post(`/projects/${id}/generate`, body).then((r) => r.data);
export const listGenerations = (id) =>
  api.get(`/projects/${id}/generations`).then((r) => r.data);
export const getGeneration = (id, gid) =>
  api.get(`/projects/${id}/generations/${gid}`).then((r) => r.data);
export const editTestCase = (id, gid, tcId, data) =>
  api.put(`/projects/${id}/generations/${gid}/testcases/${tcId}`, data).then((r) => r.data);
export const deleteTestCase = (id, gid, tcId) =>
  api.delete(`/projects/${id}/generations/${gid}/testcases/${tcId}`).then((r) => r.data);
export const approveTestCase = (id, gid, tcId) =>
  api.post(`/projects/${id}/generations/${gid}/testcases/${tcId}/approve`).then((r) => r.data);
export const addTestCase = (id, gid, data) =>
  api.post(`/projects/${id}/generations/${gid}/testcases`, data).then((r) => r.data);
export const approveGeneration = (id, gid) =>
  api.post(`/projects/${id}/generations/${gid}/approve`).then((r) => r.data);
export const stopGeneration = (id, gid) =>
  api.post(`/projects/${id}/generations/${gid}/stop`).then((r) => r.data);

// Test case sample / file uploads (manual add + edit dialogs)
export const getTestcaseSample = (id, gid, endpoint, method) =>
  api
    .get(`/projects/${id}/generations/${gid}/testcases/sample`, { params: { endpoint, method } })
    .then((r) => r.data);
export const uploadTestcaseFile = (id, gid, file) => {
  const form = new FormData();
  form.append("file", file);
  return api
    .post(`/projects/${id}/generations/${gid}/testcase-files`, form)
    .then((r) => r.data);
};
export const listTestcaseFiles = (id, gid) =>
  api.get(`/projects/${id}/generations/${gid}/testcase-files`).then((r) => r.data);

// Scenario-based generation (queued jobs)
export const submitScenarioJob = (id, gid, body) =>
  api.post(`/projects/${id}/generations/${gid}/scenario-jobs`, body).then((r) => r.data);
export const listScenarioJobs = (id) =>
  api.get(`/projects/${id}/scenario-jobs`).then((r) => r.data);
export const getScenarioJob = (id, jobId) =>
  api.get(`/projects/${id}/scenario-jobs/${jobId}`).then((r) => r.data);
export const stopScenarioJob = (id, jobId) =>
  api.post(`/projects/${id}/scenario-jobs/${jobId}/stop`).then((r) => r.data);

// Environments
export const listEnvironments = (id) => api.get(`/projects/${id}/environments`).then((r) => r.data);
export const createEnvironment = (id, body) =>
  api.post(`/projects/${id}/environments`, body).then((r) => r.data);
export const updateEnvironmentNames = (id, environments) =>
  api.put(`/projects/${id}/environments`, { environments }).then((r) => r.data);
export const deleteEnvironment = (id, envId) =>
  api.delete(`/projects/${id}/environments/${envId}`).then((r) => r.data);

// Test Users
export const listTestUsers = (id, envId) =>
  api.get(`/projects/${id}/environments/${envId}/test_users`).then((r) => r.data);
export const createTestUser = (id, envId, body) =>
  api.post(`/projects/${id}/environments/${envId}/test_users`, body).then((r) => r.data);
export const updateTestUser = (id, envId, userId, body) =>
  api.put(`/projects/${id}/environments/${envId}/test_users/${userId}`, body).then((r) => r.data);
export const deleteTestUser = (id, envId, userId) =>
  api.delete(`/projects/${id}/environments/${envId}/test_users/${userId}`).then((r) => r.data);

// Auth Config
export const getAuthConfig = (id, envId) =>
  api.get(`/projects/${id}/environments/${envId}/auth-config`).then((r) => r.data);
export const saveAuthConfig = (id, envId, config) =>
  api.put(`/projects/${id}/environments/${envId}/auth-config`, config).then((r) => r.data);
export const testAuthConfig = (id, envId, config) =>
  api.post(`/projects/${id}/environments/${envId}/auth-config/test`, config).then((r) => r.data);

// Executions
export const executeGeneration = (id, gid, body = {}) =>
  api.post(`/projects/${id}/generations/${gid}/execute`, body).then((r) => r.data);
export const listExecutions = (id) =>
  api.get(`/projects/${id}/executions`).then((r) => r.data);
export const getExecution = (id, eid) =>
  api.get(`/projects/${id}/executions/${eid}`).then((r) => r.data);
export const getExecutionResults = (id, eid) =>
  api.get(`/projects/${id}/executions/${eid}/results`).then((r) => r.data);
export const getReportUrl = (id, eid) => `/api/projects/${id}/executions/${eid}/report`;
