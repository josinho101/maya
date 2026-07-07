import { useState, useEffect, useCallback, useRef } from "react";
import {
  Box, Typography, Button, Card, CardContent, CardActions, CircularProgress, Alert,
  Accordion, AccordionSummary, AccordionDetails, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, LinearProgress, Chip, Tooltip,
  TextField, InputAdornment, Dialog, DialogContent, DialogActions,
  Tabs, Tab, Badge, Select, MenuItem, FormControl, InputLabel,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
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
import PersonIcon from "@mui/icons-material/Person";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import LockIcon from "@mui/icons-material/Lock";
import SettingsIcon from "@mui/icons-material/Settings";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  getGeneration, editTestCase, deleteTestCase, approveGeneration, approveTestCase,
  executeGeneration, triggerGeneration, stopGeneration, listScenarioJobs, stopScenarioJob,
  listEnvironments, updateEnvironmentNames, deleteEnvironment,
  listTestUsers, deleteTestUser,
  getSettings, saveSettings, testAuthConfig, addTestCase,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusChip from "../components/StatusChip";
import EditTestCaseDialog from "../components/EditTestCaseDialog";
import AddTestCaseDialog from "../components/AddTestCaseDialog";
import RegenerateDialog from "../components/RegenerateDialog";
import ClosableDialogTitle from "../components/ClosableDialogTitle";
import AddEnvironmentDialog from "../components/AddEnvironmentDialog";
import AddTestUserDialog from "../components/AddTestUserDialog";
import Toast from "../components/Toast";

const POLLING_STATUSES = ["PENDING", "GENERATING", "SCENARIOS_READY", "GENERATING_STEPS"];
const STEPS_PHASE_STATUSES = ["SCENARIOS_READY", "GENERATING_STEPS"];
const ACTIVE_JOB_STATUSES = ["QUEUED", "RUNNING"];
const VALID_TABS = ["all", "needs_review", "active", "completed", "environments", "test_users", "settings"];
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
  const [mainTab, setMainTab] = useState(
    VALID_TABS.includes(searchParams.get("jobsTab")) ? searchParams.get("jobsTab") : "all"
  );
  const [scenarioJobs, setScenarioJobs] = useState([]);
  const jobsPollRef = useRef(null);

  const [expandedSteps, setExpandedSteps] = useState(new Set());
  const [toast, setToast] = useState({ open: false, message: "" });
  const stepsToastFiredRef = useRef(false);

  const [environments, setEnvironments] = useState([]);
  const [selectedEnvId, setSelectedEnvId] = useState("");
  const [addEnvOpen, setAddEnvOpen] = useState(false);
  const [envEditTarget, setEnvEditTarget] = useState(null);
  const [envNameInput, setEnvNameInput] = useState("");
  const [envSaving, setEnvSaving] = useState(false);
  const [envDeleteTarget, setEnvDeleteTarget] = useState(null);
  const [envDeleting, setEnvDeleting] = useState(false);

  const [tuSelectedEnvId, setTuSelectedEnvId] = useState("");
  const [testUsers, setTestUsers] = useState([]);
  const [tuLoading, setTuLoading] = useState(false);
  const [revealedTu, setRevealedTu] = useState(new Set());
  const [addTuOpen, setAddTuOpen] = useState(false);
  const [editTuTarget, setEditTuTarget] = useState(null);
  const [deleteTuTarget, setDeleteTuTarget] = useState(null);
  const [tuDeleting, setTuDeleting] = useState(false);

  const [tableTestUsers, setTableTestUsers] = useState([]);
  const [duplicatingTcs, setDuplicatingTcs] = useState(new Set());

  const [settingsEnvId,      setSettingsEnvId]      = useState("");
  const [settingsSubTab,     setSettingsSubTab]     = useState("authentication");
  const [authDraft,          setAuthDraft]          = useState(null);
  const [authSaving,         setAuthSaving]         = useState(false);
  const [authSaveError,      setAuthSaveError]      = useState("");
  const [authTesting,        setAuthTesting]        = useState(false);
  const [authTestResult,     setAuthTestResult]     = useState(null);
  const [customEndpointText, setCustomEndpointText] = useState("");
  const [endpointIsCustom,   setEndpointIsCustom]   = useState(false);

  const fetchEnvironments = useCallback(async () => {
    const envs = await listEnvironments(projectId).catch(() => []);
    setEnvironments(envs);
    setSelectedEnvId((prev) => (envs.some((e) => e.id === prev) ? prev : envs[0]?.id || ""));
    return envs;
  }, [projectId]);

  useEffect(() => { fetchEnvironments(); }, [fetchEnvironments]);

  const fetchTestUsers = useCallback(async (envId) => {
    if (!envId) { setTestUsers([]); return; }
    setTuLoading(true);
    setTestUsers([]);
    try {
      setTestUsers(await listTestUsers(projectId, envId));
    } catch {
      setTestUsers([]);
    } finally {
      setTuLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    setTuSelectedEnvId((prev) => (environments.some((e) => e.id === prev) ? prev : environments[0]?.id || ""));
    setSettingsEnvId((prev) => (environments.some((e) => e.id === prev) ? prev : environments[0]?.id || ""));
  }, [environments]);

  useEffect(() => {
    setRevealedTu(new Set());
    if (mainTab === "test_users") fetchTestUsers(tuSelectedEnvId);
  }, [tuSelectedEnvId, mainTab, fetchTestUsers]);

  useEffect(() => {
    if (!selectedEnvId) { setTableTestUsers([]); return; }
    listTestUsers(projectId, selectedEnvId).then(setTableTestUsers).catch(() => setTableTestUsers([]));
  }, [projectId, selectedEnvId]);

  // Fires once, the first time this generation is observed having entered
  // the steps phase - covers both the 3s poll noticing the transition and a
  // fresh page load landing mid-phase after a refresh.
  const applyGenUpdate = useCallback((data) => {
    setGen(data);
    if (data && STEPS_PHASE_STATUSES.includes(data.status) && !stepsToastFiredRef.current) {
      stepsToastFiredRef.current = true;
      setToast({ open: true, message: "All test scenarios generated — generating test steps now" });
    }
    return data;
  }, []);

  const fetchGen = useCallback(async () => {
    try {
      const data = await getGeneration(projectId, genId);
      applyGenUpdate(data);
      return data;
    } catch {
      setError("Failed to load generation");
    } finally {
      setLoading(false);
    }
  }, [projectId, genId, applyGenUpdate]);

  useEffect(() => {
    stepsToastFiredRef.current = false;
    fetchGen().then((data) => {
      if (data && POLLING_STATUSES.includes(data.status)) {
        pollRef.current = setInterval(async () => {
          const d = await getGeneration(projectId, genId).catch(() => null);
          if (d) { applyGenUpdate(d); if (!POLLING_STATUSES.includes(d.status)) clearInterval(pollRef.current); }
        }, 3000);
      }
    });
    return () => clearInterval(pollRef.current);
  }, [projectId, genId, fetchGen, applyGenUpdate]);

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

  const handleTuSaved = (updated) => {
    setAddTuOpen(false);
    setEditTuTarget(null);
    setTestUsers(updated);
  };

  const toggleReveal = (id) => {
    setRevealedTu((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleTuDelete = async () => {
    try {
      setTuDeleting(true);
      setTestUsers(await deleteTestUser(projectId, tuSelectedEnvId, deleteTuTarget.id));
      setDeleteTuTarget(null);
    } catch (e) {
      setError(e.response?.data?.error || "Failed to delete test user");
    } finally {
      setTuDeleting(false);
    }
  };

  useEffect(() => {
    if (mainTab !== "settings" || !settingsEnvId) return;
    setAuthDraft(null);
    setAuthTestResult(null);
    setAuthSaveError("");
    setEndpointIsCustom(false);
    getSettings(projectId, settingsEnvId)
      .then((data) => {
        let cfg = data.auth || {};
        try {
          cfg = { ...cfg, request_body_template: JSON.stringify(JSON.parse(cfg.request_body_template), null, 2) };
        } catch { /* not valid JSON — leave as-is */ }
        const postEps = (gen?.testcases?.results || []).filter((r) => r.method === "POST").map((r) => r.endpoint);
        const baseUrl = (environments.find((e) => e.id === settingsEnvId)?.url || "").replace(/\/$/, "");
        const ep = cfg.auth_endpoint || "";
        // If stored as a bare path (old format), upgrade to full URL
        if (postEps.includes(ep) && baseUrl) {
          cfg = { ...cfg, auth_endpoint: baseUrl + ep };
        }
        const fullEp = cfg.auth_endpoint || "";
        const isSwaggerUrl = baseUrl && postEps.some((p) => fullEp === baseUrl + p);
        const isCustom = !!fullEp && !isSwaggerUrl;
        setEndpointIsCustom(isCustom);
        setCustomEndpointText(isCustom ? fullEp : "");
        setAuthDraft(cfg);
      })
      .catch(() => {});
  }, [settingsEnvId, mainTab, projectId]);

  const handleAuthSave = async () => {
    setAuthSaveError("");
    setAuthTestResult(null);
    if (authDraft.auth_type === "bearer_login") {
      const tpl = authDraft.request_body_template || "";
      if (!tpl.includes("{{username}}") || !tpl.includes("{{password}}")) {
        setAuthSaveError("Request body template must contain {{username}} and {{password}} placeholders.");
        return;
      }
    }
    try {
      setAuthSaving(true);
      const saved = await saveSettings(projectId, settingsEnvId, { auth: authDraft });
      setAuthDraft(saved.auth);
    } catch (e) {
      setAuthSaveError(e.response?.data?.error || "Failed to save auth config");
    } finally {
      setAuthSaving(false);
    }
  };

  const handleAuthTest = async () => {
    setAuthTestResult(null);
    const triggeredEndpoint = authDraft.auth_endpoint;
    try {
      setAuthTesting(true);
      const result = await testAuthConfig(projectId, settingsEnvId, authDraft);
      setAuthTestResult({ ...result, triggered_endpoint: triggeredEndpoint });
    } catch (e) {
      setAuthTestResult({ success: false, message: e.response?.data?.error || "Request failed", triggered_endpoint: triggeredEndpoint });
    } finally {
      setAuthTesting(false);
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

  const handleTcTestUserChange = async (tc, envId, userId) => {
    const assignments = { ...(tc.test_user_assignments || {}) };
    if (userId) assignments[envId] = userId;
    else delete assignments[envId];
    await editTestCase(projectId, genId, tc.tc_id, { ...tc, test_user_assignments: assignments });
    await fetchGen();
    setToast({ open: true, message: "Test user assignment saved" });
  };

  const handleDuplicate = async (tc, result) => {
    setDuplicatingTcs((prev) => new Set(prev).add(tc.tc_id));
    try {
      const { tc_id, source, needs_review, ...rest } = tc;
      await addTestCase(projectId, genId, {
        ...rest,
        test_scenario: `${tc.test_scenario} (Duplicate)`,
        endpoint: result.endpoint,
        method: result.method,
      });
      await fetchGen();
      setToast({ open: true, message: "Test case duplicated" });
    } catch (e) {
      setError(e.response?.data?.error || "Failed to duplicate test case");
    } finally {
      setDuplicatingTcs((prev) => {
        const next = new Set(prev);
        next.delete(tc.tc_id);
        return next;
      });
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
  const postEndpoints = results.filter((r) => r.method === "POST").map((r) => r.endpoint);
  const settingsEnvBaseUrl = (environments.find((e) => e.id === settingsEnvId)?.url || "").replace(/\/$/, "");
  const endpointSelectValue = (() => {
    if (!authDraft) return "";
    if (endpointIsCustom) return "custom";
    const ep = authDraft.auth_endpoint || "";
    if (!ep) return "";
    const path = settingsEnvBaseUrl && ep.startsWith(settingsEnvBaseUrl) ? ep.slice(settingsEnvBaseUrl.length) : ep;
    return postEndpoints.includes(path) ? path : "custom";
  })();
  const totalTc = results.reduce((n, r) => n + (r.test_cases?.length || 0), 0);
  const needsReviewCount = results.reduce(
    (n, r) => n + (r.test_cases || []).filter((tc) => tc.needs_review).length, 0
  );
  const approvedTc = totalTc - needsReviewCount;
  const activeJobs = scenarioJobs.filter((j) => ACTIVE_JOB_STATUSES.includes(j.status));
  const completedJobs = scenarioJobs.filter((j) => ["DONE", "FAILED", "CANCELLED"].includes(j.status));
  const progress = gen?.progress;

  const toggleStepsExpanded = (tcId) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(tcId)) next.delete(tcId); else next.add(tcId);
      return next;
    });
  };

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flex: 1 }}>
          <IconButton size="small" onClick={() => nav(`/projects/${projectId}`)}>
            <ArrowBackIcon fontSize="small" />
          </IconButton>
          <Typography variant="h5" fontWeight={700}>Test Cases</Typography>
        </Box>
        {gen && gen.status !== "APPROVED" && <StatusChip status={gen.status} size="medium" />}
        {results.some((r) => r.requires_auth) && selectedEnvId && tableTestUsers.length === 0 && (
          <Tooltip title="Some endpoints require authentication but no test users are configured for the selected environment — tests may fail.">
            <Chip
              icon={<LockIcon />}
              label="Auth needed — no test users configured"
              color="warning"
              size="small"
            />
          </Tooltip>
        )}
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
                {gen.status === "PENDING" && "Queued..."}
                {gen.status === "GENERATING" && "Generating test cases....."}
                {gen.status === "SCENARIOS_READY" && "Scenarios ready, starting step generation..."}
                {gen.status === "GENERATING_STEPS" && "Generating test steps....."}
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
                    {progress.completed} of {progress.total} {gen.status === "GENERATING_STEPS" ? "test cases" : "endpoints"}
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
              "& .MuiTab-root": { minHeight: 36, py: 0.5, px: 1.5, textTransform: "none" },
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
            <Tab icon={<PersonIcon fontSize="small" />} iconPosition="start" label="Test Users" value="test_users" />
            <Tab icon={<SettingsIcon fontSize="small" />} iconPosition="start" label="Settings" value="settings" />
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
                {environments.length > 0 && (
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

          {mainTab === "test_users" && (
            <Box>
              <Box sx={{ display: "flex", gap: 1.5, mb: 2, alignItems: "center", flexWrap: "wrap" }}>
                <Typography variant="body2" fontWeight={500}>Environment:</Typography>
                {environments.length > 0 ? (
                  <Select
                    size="small"
                    value={tuSelectedEnvId}
                    onChange={(e) => setTuSelectedEnvId(e.target.value)}
                    sx={{ minWidth: 180 }}
                  >
                    {environments.map((env) => (
                      <MenuItem key={env.id} value={env.id}>{env.name}</MenuItem>
                    ))}
                  </Select>
                ) : (
                  <Typography color="text.secondary" variant="body2">
                    No environments configured yet — add one in the Environments tab first.
                  </Typography>
                )}
                {isAdmin && environments.length > 0 && (
                  <Button
                    variant="outlined"
                    startIcon={<AddIcon />}
                    sx={{ ml: "auto" }}
                    onClick={() => setAddTuOpen(true)}
                  >
                    Add Test User
                  </Button>
                )}
              </Box>

              {environments.length > 0 && (
                tuLoading ? (
                  <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
                    <CircularProgress size={28} />
                  </Box>
                ) : testUsers.length === 0 ? (
                  <Typography color="text.secondary" variant="body2">No test users for this environment yet.</Typography>
                ) : (
                  <Box sx={{ minHeight: 380, backgroundColor: "background.paper" }}>
                    <Table size="small" sx={{ tableLayout: "fixed", backgroundColor: "background.paper" }}>
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ width: 220 }}>Username</TableCell>
                          <TableCell sx={{ width: 220 }}>Password</TableCell>
                          <TableCell sx={{ width: 160 }}>Roles</TableCell>
                          {isAdmin && <TableCell align="right" sx={{ width: 100 }}>Actions</TableCell>}
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {testUsers.map((u) => (
                          <TableRow key={u.id} hover>
                            <TableCell sx={{ overflowWrap: "break-word" }}>{u.username}</TableCell>
                            <TableCell sx={{ fontFamily: "monospace", overflowWrap: "break-word" }}>
                              {revealedTu.has(u.id) ? u.password : "..."}
                              <IconButton size="small" onClick={() => toggleReveal(u.id)} sx={{ ml: 0.5 }}>
                                {revealedTu.has(u.id) ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
                              </IconButton>
                            </TableCell>
                            <TableCell sx={{ overflowWrap: "break-word" }}>
                              {u.roles?.length ? (
                                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, py: 0.5 }}>
                                  {u.roles.map((r) => (
                                    <Chip key={r} label={r} size="small" variant="outlined" />
                                  ))}
                                </Box>
                              ) : "—"}
                            </TableCell>
                            {isAdmin && (
                              <TableCell align="right">
                                <Tooltip title="Edit test user">
                                  <IconButton size="small" onClick={() => setEditTuTarget(u)}>
                                    <EditIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="Delete test user">
                                  <IconButton size="small" color="error" onClick={() => setDeleteTuTarget(u)}>
                                    <DeleteIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              </TableCell>
                            )}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Box>
                )
              )}
            </Box>
          )}

          {mainTab === "settings" && (
            <Box>
              {/* Environment row with label */}
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 3 }}>
                <Typography variant="body2" fontWeight={500}>Environment:</Typography>
                {environments.length > 0 ? (
                  <Select
                    size="small"
                    value={settingsEnvId}
                    onChange={(e) => {
                      setSettingsEnvId(e.target.value);
                      setAuthTestResult(null);
                      setAuthSaveError("");
                    }}
                    sx={{ minWidth: 180 }}
                  >
                    {environments.map((env) => (
                      <MenuItem key={env.id} value={env.id}>{env.name}</MenuItem>
                    ))}
                  </Select>
                ) : (
                  <Typography color="text.secondary" variant="body2">
                    No environments configured yet — add one in the Environments tab first.
                  </Typography>
                )}
              </Box>

              {environments.length > 0 && (
                <Box>
                  {/* Sub-tabs */}
                  <Tabs
                    value={settingsSubTab}
                    onChange={(_, v) => setSettingsSubTab(v)}
                    sx={{
                      borderBottom: 1,
                      borderColor: "divider",
                      minHeight: 36,
                      "& .MuiTab-root": { minHeight: 34, py: 0.5, px: 2, textTransform: "none", fontSize: 14 },
                    }}
                  >
                    <Tab label="Authentication" value="authentication" />
                    <Tab label="Auto Trigger" value="auto_trigger" />
                  </Tabs>

                  {/* Authentication sub-tab */}
                  {settingsSubTab === "authentication" && (
                    <Box sx={{ pt: 2, bgcolor: "background.paper", p: 2 }}>
                      {/* Save at top-right */}
                      {isAdmin && (
                        <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
                          <Button
                            variant="contained"
                            onClick={handleAuthSave}
                            disabled={authSaving || authDraft === null}
                            startIcon={authSaving ? <CircularProgress size={14} /> : null}
                            sx={{ minWidth: 88 }}
                          >
                            Save
                          </Button>
                        </Box>
                      )}

                      {authDraft === null ? (
                        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                          <CircularProgress size={28} />
                        </Box>
                      ) : (
                        <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
                          {/* Auth Type + Auth Endpoint — same row, 50/50 */}
                          <Box sx={{ display: "flex", gap: 2 }}>
                            <FormControl size="small" sx={{ flex: 1 }}>
                              <InputLabel>Auth Type</InputLabel>
                              <Select
                                label="Auth Type"
                                value={authDraft.auth_type}
                                onChange={(e) => {
                                  setAuthDraft((d) => ({ ...d, auth_type: e.target.value }));
                                  setAuthTestResult(null);
                                  setAuthSaveError("");
                                }}
                              >
                                <MenuItem value="none">No Auth</MenuItem>
                                <MenuItem value="bearer_login">Bearer Token</MenuItem>
                              </Select>
                            </FormControl>
                            <FormControl size="small" sx={{ flex: 1 }} disabled={authDraft.auth_type !== "bearer_login"}>
                              <InputLabel>Auth Endpoint</InputLabel>
                              <Select
                                label="Auth Endpoint"
                                value={endpointSelectValue}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setAuthTestResult(null);
                                  if (val === "custom") {
                                    setEndpointIsCustom(true);
                                    setAuthDraft((d) => ({ ...d, auth_endpoint: customEndpointText }));
                                  } else {
                                    setEndpointIsCustom(false);
                                    setCustomEndpointText("");
                                    const baseUrl = (environments.find((env) => env.id === settingsEnvId)?.url || "").replace(/\/$/, "");
                                    setAuthDraft((d) => ({ ...d, auth_endpoint: baseUrl + val }));
                                  }
                                }}
                              >
                                {postEndpoints.map((ep) => (
                                  <MenuItem key={ep} value={ep} sx={{ fontFamily: "monospace", fontSize: 13 }}>
                                    {ep}
                                  </MenuItem>
                                ))}
                                <MenuItem value="custom" sx={{ fontStyle: "italic" }}>Custom</MenuItem>
                              </Select>
                            </FormControl>
                          </Box>

                          {authDraft.auth_type === "bearer_login" && endpointIsCustom && (
                            <TextField
                              label="Custom Auth Endpoint"
                              size="small"
                              fullWidth
                              placeholder="https://your-api.com/auth/login"
                              value={customEndpointText}
                              onChange={(e) => {
                                setCustomEndpointText(e.target.value);
                                setAuthDraft((d) => ({ ...d, auth_endpoint: e.target.value }));
                              }}
                            />
                          )}

                          {authDraft.auth_type === "bearer_login" && (
                            <>
                              <TextField
                                label="Request Body Template"
                                size="small"
                                fullWidth
                                multiline
                                rows={5}
                                value={authDraft.request_body_template}
                                onChange={(e) => setAuthDraft((d) => ({ ...d, request_body_template: e.target.value }))}
                                inputProps={{ style: { fontFamily: "monospace", fontSize: 13 } }}
                                helperText="Use {{username}} and {{password}} as placeholders — JSON key names can be anything your API expects"
                              />

                              {/* Token path + Test button inline */}
                              <Box>
                                <Box sx={{ display: "flex", gap: 1.5, alignItems: "center" }}>
                                  <TextField
                                    label="Token Path in Response"
                                    size="small"
                                    value={authDraft.token_path}
                                    onChange={(e) => setAuthDraft((d) => ({ ...d, token_path: e.target.value }))}
                                    sx={{ minWidth: 300 }}
                                  />
                                  {isAdmin && (
                                    <Button
                                      variant="outlined"
                                      onClick={handleAuthTest}
                                      disabled={authTesting}
                                      startIcon={authTesting ? <CircularProgress size={14} /> : null}
                                      sx={{ minWidth: 80 }}
                                    >
                                      Test
                                    </Button>
                                  )}
                                </Box>
                                <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5, ml: 0.25 }}>
                                  Dot-separated path, e.g. &quot;token&quot; or &quot;data.access_token&quot;
                                </Typography>
                              </Box>
                            </>
                          )}

                          {authTestResult && (
                            <Box
                              sx={{
                                border: 2,
                                borderColor: authTestResult.success ? "success.main" : "error.main",
                                borderRadius: 1,
                                p: 1.5,
                              }}
                            >
                              {authTestResult.triggered_endpoint && (
                                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                                  <Chip label="POST" size="small" color="success" />
                                  <Typography variant="body2" sx={{ fontFamily: "monospace", wordBreak: "break-all" }}>
                                    {authTestResult.triggered_endpoint}
                                  </Typography>
                                </Box>
                              )}
                              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                                {authTestResult.status_code != null && (
                                  <Chip
                                    label={`HTTP ${authTestResult.status_code}`}
                                    size="small"
                                    color={authTestResult.success ? "success" : "error"}
                                  />
                                )}
                                <Typography variant="body2">{authTestResult.message}</Typography>
                              </Box>
                              {authTestResult.response_body != null && (
                                <>
                                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                                    Full API Response:
                                  </Typography>
                                  <Box
                                    sx={{
                                      fontFamily: "monospace",
                                      fontSize: 12,
                                      whiteSpace: "pre-wrap",
                                      overflowX: "auto",
                                      bgcolor: "action.hover",
                                      p: 1,
                                      borderRadius: 0.5,
                                      maxHeight: 260,
                                      overflowY: "auto",
                                    }}
                                  >
                                    {typeof authTestResult.response_body === "string"
                                      ? authTestResult.response_body
                                      : JSON.stringify(authTestResult.response_body, null, 2)}
                                  </Box>
                                </>
                              )}
                            </Box>
                          )}

                          {authSaveError && <Alert severity="error">{authSaveError}</Alert>}
                        </Box>
                      )}
                    </Box>
                  )}

                  {/* Auto Trigger sub-tab */}
                  {settingsSubTab === "auto_trigger" && (
                    <Box sx={{ pt: 2, bgcolor: "background.paper", p: 2 }}>
                      {isAdmin && (
                        <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
                          <Button variant="contained" disabled>Save</Button>
                        </Box>
                      )}
                      <Typography color="text.secondary" variant="body2">
                        Auto trigger configuration coming soon.
                      </Typography>
                    </Box>
                  )}
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
              <Accordion key={idx} sx={{ mb: 1 }} TransitionProps={{ unmountOnExit: true }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, width: "100%" }}>
                    <Chip
                      label={result.method || "?"}
                      size="small"
                      color={METHOD_COLOR[result.method] || "default"}
                    />
                    <Typography fontFamily="monospace" fontSize={14}>{result.endpoint}</Typography>
                    <Chip label={`${filteredCases.length} cases`} size="small" variant="outlined" />
                    {result.error && <Chip label="error" size="small" color="error" />}
                    {result.requires_auth && (
                      <Tooltip title="Requires authentication">
                        <LockIcon fontSize="small" sx={{ ml: "auto", mr: 1.5 }} />
                      </Tooltip>
                    )}
                  </Box>
                </AccordionSummary>
                <AccordionDetails sx={{ p: 0 }}>
                  {result.error ? (
                    <Alert severity="error" sx={{ m: 2 }}>{result.error}</Alert>
                  ) : (
                    <Table size="small" sx={{ tableLayout: "fixed" }}>
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ width: 120 }}>TC ID</TableCell>
                          <TableCell sx={{ width: 500 }}>Test case</TableCell>
                          {result.requires_auth && <TableCell sx={{ width: 160 }}>Test User</TableCell>}
                          <TableCell sx={{ width: 150 }}>Test case Role</TableCell>
                          <TableCell sx={{ width: 70 }}>Expected Status</TableCell>
                          <TableCell align="left" sx={{ width: 90 }}>Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {filteredCases.map((tc) => (
                          <TableRow key={tc.tc_id} hover>
                            <TableCell sx={{ fontFamily: "monospace", fontSize: 12, overflowWrap: "break-word" }}>{tc.tc_id}</TableCell>
                            <TableCell sx={{ overflowWrap: "break-word" }}>
                              <Typography variant="body2" sx={{ mb: 0.5 }}>
                                Scenario: {tc.test_scenario}
                                {tc.source === "manual" && (
                                  <Chip label="manual" size="small" variant="outlined" sx={{ ml: 1 }} />
                                )}
                              </Typography>
                              <Box>
                                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                  <Typography variant="body2" sx={{ fontWeight: 700 }}>Steps:</Typography>
                                  {tc.steps_error && (
                                    <Chip label="steps failed" size="small" color="warning" variant="outlined" />
                                  )}
                                  <IconButton size="small" onClick={() => toggleStepsExpanded(tc.tc_id)}>
                                    {expandedSteps.has(tc.tc_id) ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                                  </IconButton>
                                </Box>
                                {expandedSteps.has(tc.tc_id) && !tc.steps_error && (
                                  <Box sx={{ fontFamily: "monospace", fontSize: 12, pl: 4.5 }}>
                                    {(tc.steps || []).map((line, i) => (
                                      <Typography key={i} variant="inherit" component="div" sx={{ overflowWrap: "break-word" }}>
                                        {line}
                                      </Typography>
                                    ))}
                                  </Box>
                                )}
                              </Box>
                            </TableCell>
                            {result.requires_auth && (
                              <TableCell>
                                {tc.auth_override === "missing" ? (
                                  <Typography variant="caption" color="text.secondary" sx={{ fontStyle: "italic" }}>
                                    No user needed - API will be triggered without credentials
                                  </Typography>
                                ) : tc.auth_override === "invalid" ? (
                                  <Typography variant="caption" color="text.secondary" sx={{ fontStyle: "italic" }}>
                                    No user needed - API will be triggered with invalid token
                                  </Typography>
                                ) : tableTestUsers.length > 0 ? (
                                  <Select
                                    size="small"
                                    displayEmpty
                                    value={tc.test_user_assignments?.[selectedEnvId] || ""}
                                    onChange={(e) => handleTcTestUserChange(tc, selectedEnvId, e.target.value)}
                                    sx={{ minWidth: 140, fontSize: 13 }}
                                  >
                                    <MenuItem value=""><em>None</em></MenuItem>
                                    {tableTestUsers.map((u) => (
                                      <MenuItem key={u.id} value={u.id}>{u.username}</MenuItem>
                                    ))}
                                  </Select>
                                ) : (
                                  <Typography variant="caption" color="text.secondary">—</Typography>
                                )}
                              </TableCell>
                            )}
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
                                      onClick={() => setEditTarget({ tc, endpoint: result.endpoint, method: result.method, requiresAuth: result.requires_auth })}
                                    >
                                      <EditIcon fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                  <Tooltip title="Duplicate test case">
                                    <IconButton
                                      size="small"
                                      onClick={() => handleDuplicate(tc, result)}
                                      disabled={duplicatingTcs.has(tc.tc_id)}
                                    >
                                      {duplicatingTcs.has(tc.tc_id)
                                        ? <CircularProgress size={16} />
                                        : <ContentCopyIcon fontSize="small" />}
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
        selectedEnvId={selectedEnvId}
        testUsers={tableTestUsers}
        requiresAuth={editTarget?.requiresAuth}
      />

      <AddTestCaseDialog
        open={addOpen}
        projectId={projectId}
        genId={genId}
        results={results}
        onClose={() => setAddOpen(false)}
        onAdded={() => fetchGen()}
        onScenarioQueued={handleScenarioQueued}
        selectedEnvId={selectedEnvId}
        testUsers={tableTestUsers}
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

      <AddTestUserDialog
        open={addTuOpen || !!editTuTarget}
        projectId={projectId}
        envId={tuSelectedEnvId}
        editTarget={editTuTarget}
        onClose={() => { setAddTuOpen(false); setEditTuTarget(null); }}
        onSaved={handleTuSaved}
      />

      <Dialog open={!!deleteTuTarget} onClose={() => setDeleteTuTarget(null)}>
        <ClosableDialogTitle onClose={() => setDeleteTuTarget(null)}>Delete Test User</ClosableDialogTitle>
        <DialogContent>
          <Typography>Delete <strong>{deleteTuTarget?.username}</strong>? This cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => setDeleteTuTarget(null)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleTuDelete} disabled={tuDeleting}>
            {tuDeleting ? <CircularProgress size={20} /> : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>

      <Toast
        open={toast.open}
        message={toast.message}
        onClose={() => setToast((t) => ({ ...t, open: false }))}
      />
    </Box>
  );
}
