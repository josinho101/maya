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
export const approveGeneration = (id, gid) =>
  api.post(`/projects/${id}/generations/${gid}/approve`).then((r) => r.data);

// Executions
export const executeGeneration = (id, gid) =>
  api.post(`/projects/${id}/generations/${gid}/execute`).then((r) => r.data);
export const listExecutions = (id) =>
  api.get(`/projects/${id}/executions`).then((r) => r.data);
export const getExecution = (id, eid) =>
  api.get(`/projects/${id}/executions/${eid}`).then((r) => r.data);
export const getExecutionResults = (id, eid) =>
  api.get(`/projects/${id}/executions/${eid}/results`).then((r) => r.data);
export const getReportUrl = (id, eid) => `/api/projects/${id}/executions/${eid}/report`;
