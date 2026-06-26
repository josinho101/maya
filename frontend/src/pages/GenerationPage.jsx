import { useState, useEffect, useCallback, useRef } from "react";
import {
  Box, Typography, Button, Card, CardContent, CardActions, CircularProgress, Alert,
  Accordion, AccordionSummary, AccordionDetails, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, LinearProgress, Chip, Tooltip,
  TextField, InputAdornment, Dialog, DialogContent, DialogActions,
  Tabs, Tab, Badge, Select, MenuItem,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import StopIcon from "@mui/icons-material/Stop";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import ScienceIcon from "@mui/icons-material/Science";
import FlagIcon from "@mui/icons-material/Flag";
import PendingActionsIcon from "@mui/icons-material/PendingActions";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import DnsIcon from "@mui/icons-material/Dns";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  getGeneration, editTestCase, deleteTestCase, approveGeneration, approveTestCase,
  executeGeneration, triggerGeneration, stopGeneration, listScenarioJobs, stopScenarioJob,
  listEnvironments, updateEnvironmentNames, deleteEnvironment,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusChip from "../components/StatusChip";
import EditTestCaseDialog from "../components/EditTestCaseDialog";
import AddTestCaseDialog from "../components/AddTestCaseDialog";
import RegenerateDialog from "../components/RegenerateDialog";
import ClosableDialogTitle from "../components/ClosableDialogTitle";
import AddEnvironmentDialog from "../components/AddEnvironmentDialog";

const POLLING_STATUSES = ["PENDING", "GENERATING"];
const ACTIVE_JOB_STATUSES = ["QUEUED", "RUNNING"];
const METHOD_COLOR = { GET: "info", POST: "success", PUT: "warning", PATCH: "warning", DELETE: "error" };
const LIFECYCLE_ROLE_COLOR = {
  create: "success", read: "info", update: "warning", delete: "error",
  verify_create: "secondary", verify_update: "secondary", verify_delete: "secondary",
};

export default function GenerationPage() {
  const { projectId, genId } = useParams();
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  const pollRef = useRef(null);
  const { isAdmin } = useAuth();

  const [gen, setGen] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTc, setDeleteTc] = useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [approving, setApproving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [regenOpen, setRegenOpen] = useState(false);
  const [regenEndpoints, setRegenEndpoints] = useState([]);
  const [tcSearch, setTcSearch] = useState("");
  const [mainTab, setMainTab] = useState(searchParams.get("jobsTab") === "completed" ? "completed" : "all");
  const [scenarioJobs, setScenarioJobs] = useState([]);
  const jobsPollRef = useRef(null);

  const [environments, setEnvironments] = useState([]);
  const [selectedEnvId, setSelectedEnvId] = useState("");
  const [addEnvOpen, setAddEnvOpen] = useState(false);
  const [envEditTarget, setEnvEditTarget] = useState(null);
  const [envNameInput, setEnvNameInput] = useState("");
  const [envSaving, setEnvSaving] = useState(false);
  const [envDeleteTarget, setEnvDeleteTarget] = useState(null);
  const [envDeleting, setEnvDeleting] = useState(false);

  const fetchEnvironments = useCallback(async () => {
    const envs = await listEnvironments(projectId).catch(() => []);
    setEnvironments(envs);
    setSelectedEnvId((prev) => (envs.some((e) => e.id === prev) ? prev : envs[0]?.id || ""));
    return envs;
  }, [projectId]);

  useEffect(() => { fetchEnvironments(); }, [fetchEnvironments]);

  const fetchGen = useCallback(async () => {
    try {
      const data = await getGeneration(projectId, genId);
      setGen(data);
      return data;
    } catch {
      setError("Failed to load generation");
    } finally {
      setLoading(false);
    }
  }, [projectId, genId]);

  useEffect(() => {
    fetchGen().then((data) => {
      if (data && POLLING_STATUSES.includes(data.status)) {
        pollRef.current = setInterval(async () => {
          const d = await getGeneration(projectId, genId).catch(() => null);
          if (d) { setGen(d); if (!POLLING_STATUSES.includes(d.status)) clearInterval(pollRef.current); }
        }, 3000);
      }
    });
    return () => clearInterval(pollRef.current);
  }, [projectId, genId, fetchGen]);

  // A "From Scenario" job can add a test case to this generation in the
  // background without changing gen.status, so the effect above alone won't
  // pick it up - poll separately for jobs targeting this generation and
  // refresh once they all finish.
  const refreshScenarioJobs = useCallback(async () => {
    const jobs = await listScenarioJobs(projectId).catch(() => null);
    if (!jobs) return null;
    const filtered = jobs.filter((j) => j.gen_id === genId);
    setScenarioJobs(filtered);
    return filtered;
  }, [projectId, genId]);

  // Starts the poll loop if there's active work and it isn't already
  // running - called both on mount and right after a new job is queued, so
  // the Job Queue tab count updates immediately instead of waiting for the
  // next page load to notice it.
  const ensureJobsPolling = useCallback((jobs) => {
    if (jobsPollRef.current || !jobs?.some((j) => ACTIVE_JOB_STATUSES.includes(j.status))) return;
    jobsPollRef.current = setInterval(async () => {
      const updated = await refreshScenarioJobs();
      if (updated && !updated.some((j) => ACTIVE_JOB_STATUSES.includes(j.status))) {
        clearInterval(jobsPollRef.current);
        jobsPollRef.current = null;
        fetchGen();
      }
    }, 3000);
  }, [refreshScenarioJobs, fetchGen]);

  useEffect(() => {
    refreshScenarioJobs().then(ensureJobsPolling);
    return () => { clearInterval(jobsPollRef.current); jobsPollRef.current = null; };
  }, [refreshScenarioJobs, ensureJobsPolling]);

  const handleScenarioQueued = async () => {
    ensureJobsPolling(await refreshScenarioJobs());
  };

  const handleApprove = async () => {
    try {
      setApproving(true);
      await approveGeneration(projectId, genId);
      fetchGen();
    } catch (e) {
      setError(e.response?.data?.error || "Approve failed");
    } finally {
      setApproving(false);
    }
  };

  const handleExecute = async () => {
    try {
      setExecuting(true);
      const res = await executeGeneration(projectId, genId, { environment_id: selectedEnvId });
      nav(`/projects/${projectId}/executions/${res.execution_id}`);
    } catch (e) {
      setError(e.response?.data?.error || "Execute failed");
      setExecuting(false);
    }
  };

  const handleEnvCreated = async (createdList) => {
    setAddEnvOpen(false);
    setEnvironments(createdList);
    const newest = createdList[createdList.length - 1];
    if (newest) setSelectedEnvId(newest.id);
  };

  const handleOpenEnvEdit = (env) => {
    setEnvEditTarget(env);
    setEnvNameInput(env.name);
  };

  const handleEnvRename = async () => {
    if (!envNameInput.trim()) return;
    try {
      setEnvSaving(true);
      await updateEnvironmentNames(projectId, [{ id: envEditTarget.id, name: envNameInput.trim() }]);
      await fetchEnvironments();
      setEnvEditTarget(null);
    } catch (e) {
      setError(e.response?.data?.error || "Failed to rename environment");
    } finally {
      setEnvSaving(false);
    }
  };

  const handleEnvDelete = async () => {
    try {
      setEnvDeleting(true);
      await deleteEnvironment(projectId, envDeleteTarget.id);
      await fetchEnvironments();
      setEnvDeleteTarget(null);
    } catch (e) {
      setError(e.response?.data?.error || "Failed to delete environment");
    } finally {
      setEnvDeleting(false);
    }
  };

  const handleRetry = async () => {
    try {
      setRetrying(true);
      const res = await triggerGeneration(projectId);
      nav(`/projects/${projectId}/generations/${res.generation_id}`);
    } catch (e) {
      setError(e.response?.data?.error || "Retry failed");
      setRetrying(false);
    }
  };

  const handleStop = async () => {
    try {
      setStopping(true);
      await stopGeneration(projectId, genId);
      await fetchGen();
    } catch (e) {
      setError(e.response?.data?.error || "Stop failed");
    } finally {
      setStopping(false);
    }
  };

  const handleOpenRegenerate = () => {
    setRegenEndpoints(results.map((r) => ({ endpoint: r.endpoint, method: r.method })));
    setRegenOpen(true);
  };

  const handleRegenerateConfirm = async (endpointsToRegenerate) => {
    setRegenOpen(false);
    try {
      setError("");
      // null means regenerate all; array means regenerate subset
      const body = endpointsToRegenerate !== null ? { endpoints_to_regenerate: endpointsToRegenerate } : {};
      const res = await triggerGeneration(projectId, body);
      if (!res?.generation_id) throw new Error("Invalid response from server");
      nav(`/projects/${projectId}/generations/${res.generation_id}`);
    } catch (e) {
      setError(e.response?.data?.error || e.message || "Failed to trigger regeneration");
    }
  };

  const handleStopScenarioJobOnGen = async (jobId) => {
    await stopScenarioJob(projectId, jobId).catch(() => {});
    await refreshScenarioJobs();
  };

  const handleApproveTestCase = async (tcId) => {
    try {
      await approveTestCase(projectId, genId, tcId);
      await fetchGen();
    } catch (e) {
      setError(e.response?.data?.error || "Approve failed");
    }
  };

  const handleSave = async (updated) => {
    await editTestCase(projectId, genId, updated.tc_id, updated);
    await fetchGen();
  };

  const handleDelete = async () => {
    await deleteTestCase(projectId, genId, deleteTc.tc_id);
    setDeleteTc(null);
    await fetchGen();
  };

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}><CircularProgress /></Box>;

  const results = gen?.testcases?.results || [];
  const totalTc = results.reduce((n, r) => n + (r.test_cases?.length || 0), 0);
  const needsReviewCount = results.reduce(
    (n, r) => n + (r.test_cases || []).filter((tc) => tc.needs_review).length, 0
  );
  const approvedTc = totalTc - needsReviewCount;
  const activeJobs = scenarioJobs.filter((j) => ACTIVE_JOB_STATUSES.includes(j.status));
  const completedJobs = scenarioJobs.filter((j) => ["DONE", "FAILED", "CANCELLED"].includes(j.status));
  const progress = gen?.progress;

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flex: 1 }}>
          <IconButton size="small" onClick={() => nav(`/projects/${projectId}`)}>
            <ArrowBackIcon fontSize="small" />
          </IconButton>
          <Typography variant="h5" fontWeight={700}>Generation</Typography>
        </Box>
        {gen && gen.status !== "APPROVED" && <StatusChip status={gen.status} size="medium" />}
        {isAdmin && results.length > 0 && (
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleOpenRegenerate}
          >
            Regenerate
          </Button>
        )}
        {isAdmin && results.length > 0 && (
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => setAddOpen(true)}
          >
            Add
          </Button>
        )}
      </Box>

      {/* Polling state */}
      {gen && POLLING_STATUSES.includes(gen.status) && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <Typography fontWeight={600} gutterBottom>
                {gen.status === "PENDING" ? "Queued..." : "Generating test cases....."}
              </Typography>
              {isAdmin && (
                <Button
                  size="small" color="error" variant="outlined"
                  startIcon={stopping ? <CircularProgress size={14} /> : <StopIcon fontSize="small" />}
                  onClick={handleStop} disabled={stopping}
                >
                  Stop
                </Button>
              )}
            </Box>
            {progress ? (
              <>
                <LinearProgress
                  variant="determinate"
                  value={(progress.completed / progress.total) * 100}
                  sx={{ mt: 1 }}
                />
                <Box sx={{ display: "flex", justifyContent: "space-between", mt: 0.5 }}>
                  <Typography variant="caption" color="text.secondary">
                    {progress.completed} of {progress.total} endpoints
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontFamily: "monospace" }}>
                    {progress.current}
                  </Typography>
                </Box>
              </>
            ) : (
              <>
                <LinearProgress sx={{ mt: 1 }} />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  This may take a few minutes. Polling every 3 seconds.
                </Typography>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Failed state */}
      {gen?.status === "FAILED" && (
        <Alert severity="error" sx={{ mb: 3 }}
          action={isAdmin ? (
            <Button color="inherit" size="small" startIcon={<RefreshIcon />}
              onClick={handleRetry} disabled={retrying}>
              Retry
            </Button>
          ) : null}
        >
          Generation failed: {gen.error || "Unknown error"}
        </Alert>
      )}

      {gen?.status === "STOPPED" && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Generation was stopped before all endpoints finished. The test cases
          below are whatever completed before the stop - regenerate the
          remaining endpoints from the project page when ready.
        </Alert>
      )}

      {/* Review / Approved / Stopped — test cases */}
      {gen && ["REVIEW", "APPROVED", "STOPPED"].includes(gen.status) && (
        <>
          <Tabs
            value={mainTab}
            onChange={(_, v) => setMainTab(v)}
            sx={{
              mb: 2,
              minHeight: 40,
              "& .MuiTab-root": { minHeight: 36, py: 0.5, px: 1.5 },
            }}
          >
            <Tab icon={<ScienceIcon fontSize="small" />} iconPosition="start" label={`Testcases (${approvedTc})`} value="all" />
            <Tab
              icon={<FlagIcon fontSize="small" />}
              iconPosition="start"
              label={
                <Badge badgeContent={needsReviewCount} color="warning" max={99}>
                  <Box sx={{ pr: needsReviewCount > 0 ? 1.5 : 0 }}>Needs Review</Box>
                </Badge>
              }
              value="needs_review"
            />
            <Tab icon={<PendingActionsIcon fontSize="small" />} iconPosition="start" label={`Job Queue (${activeJobs.length})`} value="active" />
            <Tab icon={<DoneAllIcon fontSize="small" />} iconPosition="start" label={`Completed Jobs (${completedJobs.length})`} value="completed" />
            <Tab icon={<DnsIcon fontSize="small" />} iconPosition="start" label="Environments" value="environments" />
          </Tabs>

          {mainTab === "needs_review" && results.every((r) => !(r.test_cases || []).some((tc) => tc.needs_review)) && (
            <Alert severity="success" sx={{ mb: 2 }}>Nothing pending review.</Alert>
          )}

          {mainTab === "needs_review" && (gen.status === "REVIEW" || needsReviewCount > 0) && isAdmin && (
            <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
              <Button
                variant="contained"
                color="success"
                startIcon={approving ? <CircularProgress size={16} /> : <CheckCircleIcon />}
                onClick={handleApprove}
                disabled={approving}
              >
                Approve All
              </Button>
            </Box>
          )}

          {mainTab === "all" && (
            <Box sx={{ display: "flex", gap: 2, mb: 2, alignItems: "center", flexWrap: "wrap" }}>
              <Typography color="text.secondary">
                {approvedTc} test cases across {results.length} endpoints
              </Typography>
              <Box sx={{ ml: "auto", display: "flex", gap: 1, alignItems: "center" }}>
                {approvedTc > 0 && (
                  <TextField
                    size="small"
                    placeholder="Search by TC ID or Scenario.."
                    value={tcSearch}
                    onChange={(e) => setTcSearch(e.target.value)}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <SearchIcon fontSize="small" />
                        </InputAdornment>
                      ),
                    }}
                    sx={{ width: 280 }}
                  />
                )}
                {gen.status === "APPROVED" && environments.length > 0 && (
                  <Select
                    size="small"
                    value={selectedEnvId}
                    onChange={(e) => setSelectedEnvId(e.target.value)}
                    sx={{ minWidth: 160 }}
                  >
                    {environments.map((env) => (
                      <MenuItem key={env.id} value={env.id}>{env.name}</MenuItem>
                    ))}
                  </Select>
                )}
                {gen.status === "APPROVED" && environments.length === 0 && (
                  <Button
                    variant="outlined"
                    startIcon={<AddIcon />}
                    onClick={() => setAddEnvOpen(true)}
                  >
                    Add Environment
                  </Button>
                )}
                {gen.status === "APPROVED" && (
                  <Tooltip title={environments.length === 0 ? "Add an environment first" : ""}>
                    <span>
                      <Button
                        variant="contained"
                        startIcon={executing ? <CircularProgress size={16} /> : <PlayArrowIcon />}
                        onClick={handleExecute}
                        disabled={executing || environments.length === 0}
                      >
                        Run
                      </Button>
                    </span>
                  </Tooltip>
                )}
              </Box>
            </Box>
          )}

          {(mainTab === "active" || mainTab === "completed") && (() => {
            const visibleJobs = mainTab === "active" ? activeJobs : completedJobs;
            return visibleJobs.length === 0 ? (
              <Typography color="text.secondary" variant="body2">
                {mainTab === "active" ? "Nothing queued or running." : "No completed jobs yet."}
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Endpoint</TableCell>
                    <TableCell>Scenario</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Result</TableCell>
                    {mainTab === "active" && <TableCell align="right">Actions</TableCell>}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {visibleJobs.map((job) => (
                    <TableRow key={job.id} hover>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>
                        {job.method} {job.endpoint}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 320, overflowWrap: "break-word" }}>{job.scenario}</TableCell>
                      <TableCell><StatusChip status={job.status} /></TableCell>
                      <TableCell>
                        {job.status === "DONE" && (
                          <Typography variant="caption" sx={{ fontFamily: "monospace" }}>{job.tc_id}</Typography>
                        )}
                        {job.status === "FAILED" && (
                          <Typography variant="caption" color="error">{job.error}</Typography>
                        )}
                      </TableCell>
                      {mainTab === "active" && (
                        <TableCell align="right">
                          {isAdmin && (
                            <Tooltip title="Stop this job">
                              <IconButton size="small" color="error" onClick={() => handleStopScenarioJobOnGen(job.id)}>
                                <StopIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            );
          })()}

          {mainTab === "environments" && (
            <Box>
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={() => setAddEnvOpen(true)}
                sx={{ mb: 2 }}
              >
                Add Environment
              </Button>
              {environments.length === 0 ? (
                <Typography color="text.secondary" variant="body2">No environments configured yet.</Typography>
              ) : (
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
                  {environments.map((env) => (
                    <Card key={env.id} sx={{ width: 220, height: 160, flex: "0 0 220px", display: "flex", flexDirection: "column" }}>
                      <CardContent sx={{ flex: 1, overflow: "hidden", p: 1.5 }}>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                          <Typography variant="subtitle1" fontWeight={600} noWrap sx={{ flex: 1 }}>{env.name}</Typography>
                        </Box>
                        <Tooltip title={env.url}>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            noWrap
                            sx={{ fontFamily: "monospace", display: "block", mb: 1 }}
                          >
                            {env.url}
                          </Typography>
                        </Tooltip>
                        <Chip
                          label={env.source === "manual" ? "Manual" : "From Spec"}
                          size="small"
                          variant="outlined"
                        />
                      </CardContent>
                      <CardActions sx={{ px: 1.5, pb: 1, pt: 0, justifyContent: "flex-end" }}>
                        <Tooltip title="Rename environment">
                          <IconButton size="small" onClick={() => handleOpenEnvEdit(env)}>
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        {env.source === "manual" && (
                          <Tooltip title="Delete environment">
                            <IconButton size="small" color="error" onClick={() => setEnvDeleteTarget(env)}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </CardActions>
                    </Card>
                  ))}
                </Box>
              )}
            </Box>
          )}

          {(mainTab === "all" || mainTab === "needs_review") && results.map((result, idx) => {
            const q = tcSearch.trim().toLowerCase();
            const filteredCases = (result.test_cases || []).filter((tc) => {
              if (mainTab === "needs_review" && !tc.needs_review) return false;
              if (mainTab === "all" && tc.needs_review) return false;
              if (!q) return true;
              return tc.tc_id?.toLowerCase().includes(q) || tc.test_scenario?.toLowerCase().includes(q);
            });
            if (filteredCases.length === 0) return null;
            return (
              <Accordion key={idx} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Chip
                      label={result.method || "?"}
                      size="small"
                      color={METHOD_COLOR[result.method] || "default"}
                    />
                    <Typography fontFamily="monospace" fontSize={14}>{result.endpoint}</Typography>
                    <Chip label={`${filteredCases.length} cases`} size="small" variant="outlined" />
                    {result.error && <Chip label="error" size="small" color="error" />}
                  </Box>
                </AccordionSummary>
                <AccordionDetails sx={{ p: 0 }}>
                  {result.error ? (
                    <Alert severity="error" sx={{ m: 2 }}>{result.error}</Alert>
                  ) : (
                    <Table size="small" sx={{ tableLayout: "fixed" }}>
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ width: 110 }}>TC ID</TableCell>
                          <TableCell>Scenario</TableCell>
                          <TableCell sx={{ width: 130 }}>Role</TableCell>
                          <TableCell sx={{ width: 140 }}>Expected Status</TableCell>
                          <TableCell align="right" sx={{ width: 100 }}>Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {filteredCases.map((tc) => (
                          <TableRow key={tc.tc_id} hover>
                            <TableCell sx={{ fontFamily: "monospace", fontSize: 12, overflowWrap: "break-word" }}>{tc.tc_id}</TableCell>
                            <TableCell sx={{ overflowWrap: "break-word" }}>
                              {tc.test_scenario}
                              {tc.source === "manual" && (
                                <Chip label="manual" size="small" variant="outlined" sx={{ ml: 1 }} />
                              )}
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={tc.lifecycle_role || "independent"}
                                size="small"
                                color={LIFECYCLE_ROLE_COLOR[tc.lifecycle_role] || "default"}
                              />
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={tc.expected_response?.status_code || "?"}
                                size="small"
                                color={tc.expected_response?.status_code < 300 ? "success" : "warning"}
                              />
                            </TableCell>
                            <TableCell align="right">
                              {isAdmin && (
                                <Box sx={{ display: "flex", flexWrap: "nowrap", justifyContent: "flex-end" }}>
                                  {tc.needs_review && (
                                    <Tooltip title="Approve this test case">
                                      <IconButton size="small" color="success" onClick={() => handleApproveTestCase(tc.tc_id)}>
                                        <CheckCircleIcon fontSize="small" />
                                      </IconButton>
                                    </Tooltip>
                                  )}
                                  <Tooltip title="Edit test case">
                                    <IconButton
                                      size="small"
                                      onClick={() => setEditTarget({ tc, endpoint: result.endpoint, method: result.method })}
                                    >
                                      <EditIcon fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                  <Tooltip title="Delete test case">
                                    <IconButton size="small" color="error" onClick={() => setDeleteTc(tc)}>
                                      <DeleteIcon fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                </Box>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </AccordionDetails>
              </Accordion>
            );
          })}
        </>
      )}

      <EditTestCaseDialog
        open={!!editTarget}
        tc={editTarget?.tc}
        endpoint={editTarget?.endpoint}
        method={editTarget?.method}
        projectId={projectId}
        genId={genId}
        onClose={() => setEditTarget(null)}
        onSave={handleSave}
      />

      <AddTestCaseDialog
        open={addOpen}
        projectId={projectId}
        genId={genId}
        results={results}
        onClose={() => setAddOpen(false)}
        onAdded={() => fetchGen()}
        onScenarioQueued={handleScenarioQueued}
      />

      <RegenerateDialog
        open={regenOpen}
        endpoints={regenEndpoints}
        loading={false}
        onClose={() => setRegenOpen(false)}
        onConfirm={handleRegenerateConfirm}
      />

      <Dialog open={!!deleteTc} onClose={() => setDeleteTc(null)}>
        <ClosableDialogTitle onClose={() => setDeleteTc(null)}>Delete Test Case</ClosableDialogTitle>
        <DialogContent>
          <Typography>Delete <strong>{deleteTc?.tc_id}</strong>? This cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => setDeleteTc(null)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>Delete</Button>
        </DialogActions>
      </Dialog>

      <AddEnvironmentDialog
        open={addEnvOpen}
        projectId={projectId}
        onClose={() => setAddEnvOpen(false)}
        onCreated={handleEnvCreated}
      />

      <Dialog open={!!envEditTarget} onClose={() => setEnvEditTarget(null)} maxWidth="sm" fullWidth>
        <ClosableDialogTitle onClose={() => setEnvEditTarget(null)}>Rename Environment</ClosableDialogTitle>
        <DialogContent>
          <TextField
            label="Name" fullWidth required sx={{ mt: 1 }}
            value={envNameInput}
            onChange={(e) => setEnvNameInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleEnvRename()}
          />
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1, fontFamily: "monospace" }}>
            {envEditTarget?.url}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => setEnvEditTarget(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleEnvRename} disabled={envSaving}>
            {envSaving ? <CircularProgress size={20} /> : "Save"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!envDeleteTarget} onClose={() => setEnvDeleteTarget(null)}>
        <ClosableDialogTitle onClose={() => setEnvDeleteTarget(null)}>Delete Environment</ClosableDialogTitle>
        <DialogContent>
          <Typography>Delete <strong>{envDeleteTarget?.name}</strong>? This cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => setEnvDeleteTarget(null)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleEnvDelete} disabled={envDeleting}>
            {envDeleting ? <CircularProgress size={20} /> : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
