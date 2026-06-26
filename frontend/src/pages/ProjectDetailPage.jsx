import { useState, useEffect, useCallback, useRef } from "react";
import {
  Box, Typography, Button, ButtonGroup, Card, CardContent, CircularProgress,
  Alert, Chip, Table, TableBody, TableCell, TableHead, TableRow,
  IconButton, Tooltip, LinearProgress, Badge,
  Dialog, DialogContent, DialogActions, TextField, Select, MenuItem,
  TablePagination,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import LinkIcon from "@mui/icons-material/Link";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import StopIcon from "@mui/icons-material/Stop";
import { useNavigate, useParams } from "react-router-dom";
import {
  getProject, uploadSwagger, importSwaggerFromUrl, triggerGeneration, getGeneration,
  listGenerations, listExecutions, getReportUrl, listScenarioJobs, stopScenarioJob,
  stopGeneration, listEnvironments,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusChip from "../components/StatusChip";
import ExecutionCharts from "../components/ExecutionCharts";
import ClosableDialogTitle from "../components/ClosableDialogTitle";
import EnvNamingDialog from "../components/EnvNamingDialog";
import AddEnvironmentDialog from "../components/AddEnvironmentDialog";

const ACTIVE_JOB_STATUSES = ["QUEUED", "RUNNING"];
const ACTIVE_GEN_STATUSES = ["PENDING", "GENERATING"];

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const nav = useNavigate();
  const fileRef = useRef();
  const { isAdmin } = useAuth();

  const [project, setProject] = useState(null);
  const [generations, setGenerations] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [environments, setEnvironments] = useState([]);
  const [selectedEnvId, setSelectedEnvId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);

  // URL import dialog state
  const [urlDialogOpen, setUrlDialogOpen] = useState(false);
  const [swaggerUrl, setSwaggerUrl] = useState("");

  // Environment naming / creation popups shown right after a swagger upload/import
  const [envNamingOpen, setEnvNamingOpen] = useState(false);
  const [pendingEnvironments, setPendingEnvironments] = useState([]);
  const [addEnvOpen, setAddEnvOpen] = useState(false);

  // Pending-review count + scenario jobs panel
  const [pendingReviewCount, setPendingReviewCount] = useState(0);
  const [scenarioJobs, setScenarioJobs] = useState([]);
  const jobsPollRef = useRef(null);

  // Executions table pagination
  const [executionsPage, setExecutionsPage] = useState(0);
  const EXECUTIONS_PER_PAGE = 7;

  const fetchAll = useCallback(async () => {
    try {
      const [proj, gens, execs, envs] = await Promise.all([
        getProject(projectId),
        listGenerations(projectId),
        listExecutions(projectId),
        listEnvironments(projectId),
      ]);
      setProject(proj);
      setGenerations(gens);
      setExecutions(execs);
      setEnvironments(envs);

      const latestGen = gens.find((g) => ["REVIEW", "APPROVED", "STOPPED"].includes(g.status));
      if (latestGen) {
        const genData = await getGeneration(projectId, latestGen.id).catch(() => null);
        const count = (genData?.testcases?.results || []).reduce(
          (n, r) => n + (r.test_cases || []).filter((tc) => tc.needs_review).length, 0
        );
        setPendingReviewCount(count);
      } else {
        setPendingReviewCount(0);
      }
    } catch {
      setError("Failed to load project");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const fetchScenarioJobs = useCallback(async () => {
    const jobs = await listScenarioJobs(projectId).catch(() => null);
    if (jobs) setScenarioJobs(jobs);
    return jobs;
  }, [projectId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  useEffect(() => {
    const hasActiveWork = (jobs, gens) =>
      jobs?.some((j) => ACTIVE_JOB_STATUSES.includes(j.status)) ||
      gens?.some((g) => ACTIVE_GEN_STATUSES.includes(g.status));

    const checkOnce = async () => {
      const [jobs, gens] = await Promise.all([
        fetchScenarioJobs(),
        listGenerations(projectId).catch(() => null),
      ]);
      if (gens) setGenerations(gens);
      return { jobs, gens };
    };

    checkOnce().then(({ jobs, gens }) => {
      if (hasActiveWork(jobs, gens)) {
        jobsPollRef.current = setInterval(async () => {
          const updated = await checkOnce();
          if (!hasActiveWork(updated.jobs, updated.gens)) {
            clearInterval(jobsPollRef.current);
            fetchAll();
          }
        }, 3000);
      }
    });
    return () => clearInterval(jobsPollRef.current);
  }, [fetchScenarioJobs, fetchAll, projectId]);

  useEffect(() => {
    if (environments.length > 0 && !environments.some((e) => e.id === selectedEnvId)) {
      setSelectedEnvId(environments[0].id);
    }
  }, [environments, selectedEnvId]);

  useEffect(() => { setExecutionsPage(0); }, [executions]);

  const handleStopScenarioJob = async (jobId) => {
    await stopScenarioJob(projectId, jobId).catch(() => {});
    fetchScenarioJobs();
  };

  const handleStopGenerationJob = async (genJobId) => {
    await stopGeneration(projectId, genJobId).catch(() => {});
    const updated = await listGenerations(projectId).catch(() => null);
    if (updated) setGenerations(updated);
  };

  const handleEnvFlags = (res) => {
    if (res.needs_env_naming) {
      setPendingEnvironments(res.environments);
      setEnvNamingOpen(true);
    } else if (res.no_servers_found) {
      setAddEnvOpen(true);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setUploading(true);
      setError("");
      const res = await uploadSwagger(projectId, file);
      handleEnvFlags(res);
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.error || "Upload failed");
    } finally {
      setUploading(false);
      fileRef.current.value = "";
    }
  };

  const handleImportFromUrl = async () => {
    if (!swaggerUrl.trim()) return;
    try {
      setUploading(true);
      setError("");
      const res = await importSwaggerFromUrl(projectId, swaggerUrl.trim());
      handleEnvFlags(res);
      setUrlDialogOpen(false);
      setSwaggerUrl("");
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.error || "Import failed");
    } finally {
      setUploading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError("");
      const res = await triggerGeneration(projectId);
      if (!res?.generation_id) throw new Error("Invalid response from server");
      nav(`/projects/${projectId}/generations/${res.generation_id}`);
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Failed to trigger generation");
      setGenerating(false);
    }
  };

  const handleViewTestCases = () => {
    // Most recent generation regardless of status - listGenerations already
    // returns them sorted by created_at desc - so this always has somewhere
    // to go as soon as one generation exists, not just REVIEW/APPROVED ones.
    if (generations[0]) nav(`/projects/${projectId}/generations/${generations[0].id}`);
  };

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}><CircularProgress /></Box>;
  if (!project) return <Alert severity="error">Project not found</Alert>;

  const swagger = project.swagger;
  const hasAnyGeneration = generations.length > 0;
  const activeGen = generations.find((g) => ACTIVE_GEN_STATUSES.includes(g.status));

  const genRows = generations.map((g) => ({ kind: "generation", id: g.id, status: g.status, created_at: g.created_at }));
  const scenarioRows = scenarioJobs.map((j) => ({ kind: "scenario", id: j.id, status: j.status, created_at: j.created_at, job: j }));
  const sortByCreatedDesc = (a, b) => (b.created_at || "").localeCompare(a.created_at || "");

  const activeQueueRows = [
    ...genRows.filter((r) => ACTIVE_GEN_STATUSES.includes(r.status)),
    ...scenarioRows.filter((r) => ACTIVE_JOB_STATUSES.includes(r.status)),
  ].sort(sortByCreatedDesc);

  const completedQueueRows = [
    ...genRows.filter((r) => !ACTIVE_GEN_STATUSES.includes(r.status)),
    ...scenarioRows.filter((r) => ["DONE", "FAILED", "CANCELLED"].includes(r.status)),
  ].sort(sortByCreatedDesc);

  const completedJobsTargetGenId = generations.find((g) => ["REVIEW", "APPROVED", "STOPPED"].includes(g.status))?.id;

  const filteredExecutions = environments.length > 0
    ? executions.filter((e) => e.environment_id === selectedEnvId)
    : executions;

  const sortedExecutions = [...executions].sort(
    (a, b) => (b.started_at || "").localeCompare(a.started_at || "")
  );
  const pagedExecutions = sortedExecutions.slice(
    executionsPage * EXECUTIONS_PER_PAGE,
    executionsPage * EXECUTIONS_PER_PAGE + EXECUTIONS_PER_PAGE
  );

  return (
    <Box>
      {/* Compact page header */}
      <Box sx={{ mb: 1.5 }}>
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, flexDirection: { xs: "column", md: "row" } }}>

          {/* Left: back nav + title + description */}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <IconButton size="small" onClick={() => nav("/projects")}>
                <ArrowBackIcon fontSize="small" />
              </IconButton>
              <Typography variant="h5" fontWeight={700}>{project.name}</Typography>
            </Box>
            {project.description && (
              <Typography variant="body2" color="text.secondary" sx={{ ml: 4.5, mt: 0.25 }}>
                {project.description}
              </Typography>
            )}
          </Box>

          {/* Right: upload actions + conditional test case buttons + metadata chips below */}
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 0.75, flexShrink: 0 }}>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center", justifyContent: "flex-end" }}>
            {isAdmin && (
              <>
                <input
                  type="file" accept=".yaml,.yml,.json" ref={fileRef}
                  style={{ display: "none" }} onChange={handleUpload}
                />
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Typography variant="caption" color="text.secondary">Upload Swagger</Typography>
                  <ButtonGroup size="small" variant="outlined" disabled={uploading}>
                    <Tooltip title={swagger ? "Re-upload Swagger" : "Upload Swagger"}>
                      <Button onClick={() => fileRef.current.click()}>
                        {uploading ? <CircularProgress size={14} /> : <UploadFileIcon fontSize="small" />}
                      </Button>
                    </Tooltip>
                    <Tooltip title="Import from URL">
                      <Button onClick={() => setUrlDialogOpen(true)}>
                        <LinkIcon fontSize="small" />
                      </Button>
                    </Tooltip>
                  </ButtonGroup>
                </Box>
              </>
            )}
            {swagger && !hasAnyGeneration && !activeGen && !generating && isAdmin && (
              <Button variant="contained" size="small" startIcon={<PlayArrowIcon />} onClick={handleGenerate}>
                Generate Test Cases
              </Button>
            )}
            {swagger && hasAnyGeneration && (
              <Badge badgeContent={pendingReviewCount} color="warning" max={99}>
                <Button variant="outlined" size="small" startIcon={<OpenInNewIcon />} onClick={handleViewTestCases}>
                  View Test Cases
                </Button>
              </Badge>
            )}
            {swagger && (activeGen || generating) && (
              <Button
                variant="outlined" color="warning" size="small"
                startIcon={<CircularProgress size={16} />}
                onClick={activeGen ? () => nav(`/projects/${projectId}/generations/${activeGen.id}`) : undefined}
                disabled={!activeGen}
              >
                View Progress
              </Button>
            )}
            </Box>
            {(environments.length > 0 || (swagger && swagger.endpoint_count != null)) && (
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center", justifyContent: "flex-end", mt: 0.5 }}>
                {environments.length > 0 && (
                  <>
                    <Typography variant="caption" color="text.secondary">Environment</Typography>
                    <Select
                      size="small"
                      value={selectedEnvId}
                      onChange={(e) => setSelectedEnvId(e.target.value)}
                      sx={{ minWidth: 160, fontSize: 13, "& .MuiSelect-select": { py: 0.5 } }}
                    >
                      {environments.map((env) => (
                        <MenuItem key={env.id} value={env.id} sx={{ fontSize: 13 }}>{env.name}</MenuItem>
                      ))}
                    </Select>
                  </>
                )}
                {swagger && swagger.endpoint_count != null && (
                  <Chip label={`${swagger.endpoint_count} endpoints`} color="primary" size="small" />
                )}
              </Box>
            )}
          </Box>
        </Box>
        {uploading && <LinearProgress sx={{ mt: 1 }} />}
        {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
      </Box>

      <Box sx={{ mt: 3 }}>
        <ExecutionCharts executions={filteredExecutions} />
      </Box>

      {/* Executions */}
      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight={600} gutterBottom>Executions</Typography>
          {executions.length === 0 ? (
            <Typography color="text.secondary">No executions yet</Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Environment</TableCell>
                  <TableCell>Pass</TableCell>
                  <TableCell>Fail</TableCell>
                  <TableCell>Rate</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pagedExecutions.map((e) => (
                  <TableRow key={e.id} hover>
                    <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{e.id}</TableCell>
                    <TableCell><StatusChip status={e.status} /></TableCell>
                    <TableCell>{e.environment_name || "—"}</TableCell>
                    <TableCell sx={{ color: "success.main" }}>{e.summary?.passed ?? "—"}</TableCell>
                    <TableCell sx={{ color: "error.main" }}>{e.summary?.failed ?? "—"}</TableCell>
                    <TableCell>
                      {e.summary ? `${e.summary.success_rate}%` : "—"}
                    </TableCell>
                    <TableCell>{new Date(e.started_at).toLocaleString()}</TableCell>
                    <TableCell align="right">
                      <Button size="small" onClick={() => nav(`/projects/${projectId}/executions/${e.id}`)}>
                        View
                      </Button>
                      {e.status === "COMPLETED" && (
                        <Tooltip title="Open HTML report">
                          <IconButton size="small" onClick={() => window.open(getReportUrl(projectId, e.id), "_blank")}>
                            <OpenInNewIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {executions.length > EXECUTIONS_PER_PAGE && (
            <TablePagination
              component="div"
              count={sortedExecutions.length}
              page={executionsPage}
              onPageChange={(_, newPage) => setExecutionsPage(newPage)}
              rowsPerPage={EXECUTIONS_PER_PAGE}
              rowsPerPageOptions={[EXECUTIONS_PER_PAGE]}
            />
          )}
        </CardContent>
      </Card>

      {/* Active queue: currently queued/running full-generation runs + scenario jobs */}
      {activeQueueRows.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} gutterBottom>Job Queue</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Type</TableCell>
                  <TableCell>Endpoint</TableCell>
                  <TableCell>Scenario</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Result</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {activeQueueRows.map((row) =>
                  row.kind === "generation" ? (
                    <TableRow key={`gen-${row.id}`} hover>
                      <TableCell>Full Generation</TableCell>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>All endpoints</TableCell>
                      <TableCell>—</TableCell>
                      <TableCell><StatusChip status={row.status} /></TableCell>
                      <TableCell>
                        <Button size="small" onClick={() => nav(`/projects/${projectId}/generations/${row.id}`)}>
                          View Progress
                        </Button>
                      </TableCell>
                      <TableCell align="right">
                        {isAdmin && (
                          <Tooltip title="Stop this generation">
                            <IconButton size="small" color="error" onClick={() => handleStopGenerationJob(row.id)}>
                              <StopIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ) : (
                    <TableRow key={`job-${row.id}`} hover>
                      <TableCell>Scenario</TableCell>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>
                        {row.job.method} {row.job.endpoint}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 320, overflowWrap: "break-word" }}>{row.job.scenario}</TableCell>
                      <TableCell><StatusChip status={row.job.status} /></TableCell>
                      <TableCell>—</TableCell>
                      <TableCell align="right">
                        {isAdmin && (
                          <Tooltip title="Stop this job">
                            <IconButton size="small" color="error" onClick={() => handleStopScenarioJob(row.job.id)}>
                              <StopIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Completed jobs: glance-only history, capped to the 10 most recent */}
      {completedQueueRows.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} gutterBottom>Completed Jobs Queue</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Type</TableCell>
                  <TableCell>Endpoint</TableCell>
                  <TableCell>Scenario</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Result</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {completedQueueRows.slice(0, 10).map((row) =>
                  row.kind === "generation" ? (
                    <TableRow key={`gen-${row.id}`} hover>
                      <TableCell>Full Generation</TableCell>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>All endpoints</TableCell>
                      <TableCell>—</TableCell>
                      <TableCell><StatusChip status={row.status} /></TableCell>
                      <TableCell>—</TableCell>
                    </TableRow>
                  ) : (
                    <TableRow key={`job-${row.id}`} hover>
                      <TableCell>Scenario</TableCell>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>
                        {row.job.method} {row.job.endpoint}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 320, overflowWrap: "break-word" }}>{row.job.scenario}</TableCell>
                      <TableCell><StatusChip status={row.job.status} /></TableCell>
                      <TableCell>
                        {row.job.status === "DONE" && (
                          <Typography variant="caption" sx={{ fontFamily: "monospace" }}>{row.job.tc_id}</Typography>
                        )}
                        {row.job.status === "FAILED" && (
                          <Typography variant="caption" color="error">{row.job.error}</Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                )}
              </TableBody>
            </Table>
            {completedQueueRows.length > 10 && completedJobsTargetGenId && (
              <Button
                size="small"
                sx={{ mt: 1 }}
                onClick={() => nav(`/projects/${projectId}/generations/${completedJobsTargetGenId}?jobsTab=completed`)}
              >
                View More
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      <Dialog
        open={urlDialogOpen}
        onClose={() => { setUrlDialogOpen(false); setSwaggerUrl(""); }}
        fullWidth
        maxWidth="sm"
      >
        <ClosableDialogTitle onClose={() => { setUrlDialogOpen(false); setSwaggerUrl(""); }}>
          Import from URL
        </ClosableDialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="URL"
            placeholder="https://example.com/openapi.json"
            value={swaggerUrl}
            onChange={(e) => setSwaggerUrl(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleImportFromUrl(); }}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => { setUrlDialogOpen(false); setSwaggerUrl(""); }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleImportFromUrl}
            disabled={uploading || !swaggerUrl.trim()}
            startIcon={uploading ? <CircularProgress size={16} /> : null}
          >
            Import
          </Button>
        </DialogActions>
      </Dialog>

      <EnvNamingDialog
        open={envNamingOpen}
        projectId={projectId}
        environments={pendingEnvironments}
        onClose={() => setEnvNamingOpen(false)}
        onSaved={() => { setEnvNamingOpen(false); fetchAll(); }}
      />

      <AddEnvironmentDialog
        open={addEnvOpen}
        projectId={projectId}
        title="No environment found in this spec — add one to get started"
        onClose={() => setAddEnvOpen(false)}
        onCreated={() => { setAddEnvOpen(false); fetchAll(); }}
      />
    </Box>
  );
}
