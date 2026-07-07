import { useState, useEffect, useCallback, useRef, startTransition } from "react";
import {
  Box, Typography, Button, Card, CardContent, CircularProgress, Alert,
  LinearProgress, Chip, Tooltip, Tabs, Tab, Badge, IconButton,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import RefreshIcon from "@mui/icons-material/Refresh";
import AddIcon from "@mui/icons-material/Add";
import StopIcon from "@mui/icons-material/Stop";
import ScienceIcon from "@mui/icons-material/Science";
import FlagIcon from "@mui/icons-material/Flag";
import PendingActionsIcon from "@mui/icons-material/PendingActions";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import DnsIcon from "@mui/icons-material/Dns";
import PersonIcon from "@mui/icons-material/Person";
import SettingsIcon from "@mui/icons-material/Settings";
import LockIcon from "@mui/icons-material/Lock";
import HistoryIcon from "@mui/icons-material/History";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  getGeneration, triggerGeneration, stopGeneration,
  listScenarioJobs, stopScenarioJob,
  listEnvironments, listTestUsers,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusChip from "../components/StatusChip";
import AddTestCaseDialog from "../components/AddTestCaseDialog";
import RegenerateDialog from "../components/RegenerateDialog";
import Toast from "../components/Toast";
import TestCasesTab from "../components/tabs/TestCasesTab";
import JobQueueTab from "../components/tabs/JobQueueTab";
import EnvironmentsTab from "../components/tabs/EnvironmentsTab";
import TestUsersTab from "../components/tabs/TestUsersTab";
import SettingsTab from "../components/tabs/SettingsTab";
import GenerationsTab from "../components/tabs/GenerationsTab";

const POLLING_STATUSES = ["PENDING", "GENERATING", "SCENARIOS_READY", "GENERATING_STEPS"];
const STEPS_PHASE_STATUSES = ["SCENARIOS_READY", "GENERATING_STEPS"];
const ACTIVE_JOB_STATUSES = ["QUEUED", "RUNNING"];
const VALID_TABS = ["all", "needs_review", "active", "completed", "environments", "test_users", "settings", "generations"];

export default function GenerationPage() {
  const { projectId, genId } = useParams();
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  const pollRef = useRef(null);
  const { isAdmin } = useAuth();

  const [gen, setGen] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [regenOpen, setRegenOpen] = useState(false);
  const [regenEndpoints, setRegenEndpoints] = useState([]);
  const [addOpen, setAddOpen] = useState(false);
  const [mainTab, setMainTab] = useState(
    VALID_TABS.includes(searchParams.get("jobsTab")) ? searchParams.get("jobsTab") : "all"
  );
  const [scenarioJobs, setScenarioJobs] = useState([]);
  const jobsPollRef = useRef(null);

  const [toast, setToast] = useState({ open: false, message: "" });
  const stepsToastFiredRef = useRef(false);

  const [environments, setEnvironments] = useState([]);
  const [selectedEnvId, setSelectedEnvId] = useState("");
  const [tableTestUsers, setTableTestUsers] = useState([]);
  const [testUsersLoading, setTestUsersLoading] = useState(false);

  const fetchEnvironments = useCallback(async () => {
    const envs = await listEnvironments(projectId).catch(() => []);
    setEnvironments(envs);
    setSelectedEnvId((prev) => (envs.some((e) => e.id === prev) ? prev : envs[0]?.id || ""));
    return envs;
  }, [projectId]);

  useEffect(() => { fetchEnvironments(); }, [fetchEnvironments]);

  useEffect(() => {
    if (!selectedEnvId) { setTableTestUsers([]); return; }
    setTestUsersLoading(true);
    listTestUsers(projectId, selectedEnvId)
      .then(setTableTestUsers)
      .catch(() => setTableTestUsers([]))
      .finally(() => setTestUsersLoading(false));
  }, [projectId, selectedEnvId]);

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

  const refreshScenarioJobs = useCallback(async () => {
    const jobs = await listScenarioJobs(projectId).catch(() => null);
    if (!jobs) return null;
    const filtered = jobs.filter((j) => j.gen_id === genId);
    setScenarioJobs(filtered);
    return filtered;
  }, [projectId, genId]);

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

  const handleEnvCreated = (createdList) => {
    setEnvironments(createdList);
    const newest = createdList[createdList.length - 1];
    if (newest) setSelectedEnvId(newest.id);
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
          <Typography variant="h5" fontWeight={700}>Test Cases</Typography>
        </Box>
        {gen && gen.status !== "APPROVED" && <StatusChip status={gen.status} size="medium" />}
        {results.some((r) => r.requires_auth) && selectedEnvId && !testUsersLoading && tableTestUsers.length === 0 && (
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
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={handleOpenRegenerate}>
            Regenerate
          </Button>
        )}
        {isAdmin && results.length > 0 && (
          <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setAddOpen(true)}>
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

      {/* Tabs */}
      {gen && ["REVIEW", "APPROVED", "STOPPED"].includes(gen.status) && (
        <>
          <Tabs
            value={mainTab}
            onChange={(_, v) => startTransition(() => setMainTab(v))}
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
            <Tab icon={<HistoryIcon fontSize="small" />} iconPosition="start" label="Generations" value="generations" />
            <Tab icon={<PendingActionsIcon fontSize="small" />} iconPosition="start" label={`Job Queue (${activeJobs.length})`} value="active" />
            <Tab icon={<DoneAllIcon fontSize="small" />} iconPosition="start" label={`Completed Jobs (${completedJobs.length})`} value="completed" />
            <Tab icon={<DnsIcon fontSize="small" />} iconPosition="start" label="Environments" value="environments" />
            <Tab icon={<PersonIcon fontSize="small" />} iconPosition="start" label="Test Users" value="test_users" />
            <Tab icon={<SettingsIcon fontSize="small" />} iconPosition="start" label="Settings" value="settings" />
          </Tabs>

          {(mainTab === "all" || mainTab === "needs_review") && (
            <TestCasesTab
              gen={gen}
              genId={genId}
              projectId={projectId}
              isAdmin={isAdmin}
              mainTab={mainTab}
              environments={environments}
              selectedEnvId={selectedEnvId}
              onSelectedEnvIdChange={setSelectedEnvId}
              tableTestUsers={tableTestUsers}
              onFetchGen={fetchGen}
              onSwitchToEnvironments={() => setMainTab("environments")}
            />
          )}

          {(mainTab === "active" || mainTab === "completed") && (
            <JobQueueTab
              jobs={mainTab === "active" ? activeJobs : completedJobs}
              isActive={mainTab === "active"}
              isAdmin={isAdmin}
              onStopJob={handleStopScenarioJobOnGen}
            />
          )}

          {mainTab === "environments" && (
            <EnvironmentsTab
              environments={environments}
              projectId={projectId}
              isAdmin={isAdmin}
              onEnvCreated={handleEnvCreated}
              onRefreshEnvironments={fetchEnvironments}
            />
          )}

          {mainTab === "test_users" && (
            <TestUsersTab
              environments={environments}
              projectId={projectId}
              isAdmin={isAdmin}
            />
          )}

          {mainTab === "settings" && (
            <SettingsTab
              environments={environments}
              projectId={projectId}
              isAdmin={isAdmin}
              gen={gen}
            />
          )}

          {mainTab === "generations" && (
            <GenerationsTab
              projectId={projectId}
              thisGenId={genId}
              isAdmin={isAdmin}
            />
          )}
        </>
      )}

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

      <Toast
        open={toast.open}
        message={toast.message}
        onClose={() => setToast((t) => ({ ...t, open: false }))}
      />
    </Box>
  );
}
