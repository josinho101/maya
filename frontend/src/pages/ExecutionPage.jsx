import { useState, useEffect, useCallback, useRef } from "react";
import {
  Box, Typography, Button, Card, CardContent, CircularProgress, Alert,
  LinearProgress, Grid, Divider, Chip, List, ListItemButton, ListItemText,
  ListItemIcon, Tooltip, Accordion, AccordionSummary, AccordionDetails,
  Table, TableHead, TableRow, TableCell, TableBody, IconButton,
  TextField, InputAdornment, Dialog, DialogContent, DialogActions,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutlined";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlined";
import HistoryIcon from "@mui/icons-material/History";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useNavigate, useParams } from "react-router-dom";
import {
  getExecution, listExecutions, executeGeneration, getReportUrl,
  getGeneration, editTestCase, deleteTestCase,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusChip from "../components/StatusChip";
import EditTestCaseDialog from "../components/EditTestCaseDialog";
import ClosableDialogTitle from "../components/ClosableDialogTitle";

const POLLING_STATUSES = ["PENDING", "RUNNING"];
const METHOD_COLOR = { GET: "info", POST: "success", PUT: "warning", PATCH: "warning", DELETE: "error" };
const LIFECYCLE_ROLE_COLOR = {
  create: "success", read: "info", update: "warning", delete: "error",
  verify_create: "secondary", verify_update: "secondary", verify_delete: "secondary",
};

function SummaryCard({ label, value, color }) {
  return (
    <Card>
      <CardContent sx={{ textAlign: "center" }}>
        <Typography variant="h3" fontWeight={700} color={color}>{value ?? "—"}</Typography>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
      </CardContent>
    </Card>
  );
}

export default function ExecutionPage() {
  const { execId } = useParams();
  return <ExecutionPageInner key={execId} />;
}

function ExecutionPageInner() {
  const { projectId, execId } = useParams();
  const nav = useNavigate();
  const pollRef = useRef(null);
  const { isAdmin } = useAuth();

  const [exec, setExec] = useState(null);
  const [gen, setGen] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rerunning, setRerunning] = useState(false);
  const [editTc, setEditTc] = useState(null);
  const [deleteTc, setDeleteTc] = useState(null);
  const [tcSearch, setTcSearch] = useState("");

  const fetchExec = useCallback(async () => {
    try {
      const data = await getExecution(projectId, execId);
      setExec(data);
      return data;
    } catch {
      setError("Failed to load execution");
    } finally {
      setLoading(false);
    }
  }, [projectId, execId]);

  const fetchHistory = useCallback(async () => {
    try {
      const all = await listExecutions(projectId);
      setHistory(all);
    } catch { /* ignore */ }
  }, [projectId]);

  const fetchGen = useCallback(async (genId) => {
    try {
      const data = await getGeneration(projectId, genId);
      setGen(data);
    } catch { /* ignore */ }
  }, [projectId]);

  useEffect(() => {
    fetchExec().then((data) => {
      if (!data) return;
      fetchGen(data.generation_id);
      if (POLLING_STATUSES.includes(data.status)) {
        pollRef.current = setInterval(async () => {
          const d = await getExecution(projectId, execId).catch(() => null);
          if (d) {
            setExec(d);
            if (!POLLING_STATUSES.includes(d.status)) {
              clearInterval(pollRef.current);
              fetchHistory();
            }
          }
        }, 5000);
      }
    });
    fetchHistory();
    return () => clearInterval(pollRef.current);
  }, [projectId, execId, fetchExec, fetchHistory, fetchGen]);

  const handleRerun = async () => {
    try {
      setRerunning(true);
      const res = await executeGeneration(projectId, exec.generation_id, { environment_id: exec.environment_id });
      nav(`/projects/${projectId}/executions/${res.execution_id}`);
    } catch (e) {
      setError(e.response?.data?.error || "Re-run failed");
      setRerunning(false);
    }
  };

  const handleSaveEdit = async (updated) => {
    await editTestCase(projectId, exec.generation_id, updated.tc_id, updated);
    await fetchGen(exec.generation_id);
  };

  const handleDelete = async () => {
    await deleteTestCase(projectId, exec.generation_id, deleteTc.tc_id);
    setDeleteTc(null);
    await fetchGen(exec.generation_id);
  };

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}><CircularProgress /></Box>;

  const summary = exec?.summary;
  const tcResults = gen?.testcases?.results || [];
  const totalTc = tcResults.reduce((n, r) => n + (r.test_cases?.length || 0), 0);
  const canRerun = exec?.status === "COMPLETED" || exec?.status === "FAILED";

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ display: "flex", gap: 2, mb: 3, alignItems: "center", flexWrap: "wrap" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flex: 1 }}>
          <IconButton size="small" onClick={() => nav(`/projects/${projectId}`)}>
            <ArrowBackIcon fontSize="small" />
          </IconButton>
          <Typography variant="h5" fontWeight={700}>Execution</Typography>
        </Box>
        <Chip label={`ID: ${execId}`} size="small" sx={{ fontFamily: "monospace" }} />
        {exec?.environment_name && <Chip label={exec.environment_name} size="small" color="secondary" variant="outlined" />}
      </Box>

      <Box sx={{ display: "flex", gap: 3, alignItems: "flex-start", flexDirection: { xs: "column", md: "row" } }}>
        {/* Left: results */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {/* Polling */}
          {exec && POLLING_STATUSES.includes(exec.status) && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography fontWeight={600} gutterBottom>
                  {exec.status === "PENDING" ? "Queued..." : "Running test cases..."}
                </Typography>
                <LinearProgress sx={{ mt: 1 }} />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  Polling every 5 seconds.
                </Typography>
              </CardContent>
            </Card>
          )}

          {/* Failed */}
          {exec?.status === "FAILED" && (
            <Alert severity="error" sx={{ mb: 3 }}>
              Execution failed: {exec.error || "Unknown error"}
            </Alert>
          )}

          {/* Completed summary */}
          {exec?.status === "COMPLETED" && summary && (
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={6} sm={3}>
                <SummaryCard label="Total" value={summary.total} color="text.primary" />
              </Grid>
              <Grid item xs={6} sm={3}>
                <SummaryCard label="Passed" value={summary.passed} color="success.main" />
              </Grid>
              <Grid item xs={6} sm={3}>
                <SummaryCard label="Failed" value={summary.failed} color="error.main" />
              </Grid>
              <Grid item xs={6} sm={3}>
                <SummaryCard label="Skipped" value={summary.skipped} color="text.secondary" />
              </Grid>
              <Grid item xs={6} sm={3}>
                <SummaryCard label="Success Rate" value={`${summary.success_rate}%`}
                  color={summary.success_rate >= 80 ? "success.main" : "warning.main"} />
              </Grid>
            </Grid>
          )}

          {/* Action buttons */}
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 3, alignItems: "center" }}>
            {exec?.status === "COMPLETED" && (
              <Button
                variant="contained"
                startIcon={<OpenInNewIcon />}
                onClick={() => window.open(getReportUrl(projectId, execId), "_blank")}
              >
                View Full Report
              </Button>
            )}
            {canRerun && (
              <Button
                variant="outlined"
                startIcon={rerunning ? <CircularProgress size={16} /> : <PlayArrowIcon />}
                onClick={handleRerun}
                disabled={rerunning}
              >
                Re-run Tests
              </Button>
            )}
            {tcResults.length > 0 && (
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
                sx={{ width: 280, ml: "auto" }}
              />
            )}
          </Box>

          {/* Test cases accordion with inline editing */}
          {tcResults.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 2 }}>
                Test Cases ({totalTc})
              </Typography>
              {tcResults.map((result, idx) => {
                const q = tcSearch.trim().toLowerCase();
                const filteredCases = q
                  ? (result.test_cases || []).filter(
                      (tc) =>
                        tc.tc_id?.toLowerCase().includes(q) ||
                        tc.test_scenario?.toLowerCase().includes(q)
                    )
                  : (result.test_cases || []);
                if (filteredCases.length === 0) return null;
                return (
                  <Accordion key={idx} sx={{ mb: 1, width: "100%" }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                        <Chip
                          label={result.method || "?"}
                          size="small"
                          color={METHOD_COLOR[result.method] || "default"}
                        />
                        <Typography fontFamily="monospace" fontSize={14}>{result.endpoint}</Typography>
                        <Chip
                          label={`${filteredCases.length}${q ? `/${result.test_cases?.length || 0}` : ""} cases`}
                          size="small"
                          variant="outlined"
                        />
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
                                <TableCell sx={{ overflowWrap: "break-word" }}>{tc.test_scenario}</TableCell>
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
                                      <Tooltip title="Edit test case">
                                        <IconButton size="small" onClick={() => setEditTc(tc)}>
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
            </Box>
          )}
        </Box>

        {/* Right: execution history */}
        <Box sx={{ width: { xs: "100%", md: 320 }, flexShrink: 0 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                <HistoryIcon fontSize="small" color="primary" />
                <Typography fontWeight={600}>Execution History</Typography>
              </Box>
              <Divider sx={{ mb: 1 }} />
              {history.length === 0 ? (
                <Typography variant="body2" color="text.secondary">No history</Typography>
              ) : (
                <List dense disablePadding>
                  {history.map((h) => {
                    const isCurrent = h.id === execId;
                    return (
                      <ListItemButton
                        key={h.id}
                        selected={isCurrent}
                        onClick={() => !isCurrent && nav(`/projects/${projectId}/executions/${h.id}`)}
                        sx={{ borderRadius: 1, mb: 0.5 }}
                      >
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          {h.status === "COMPLETED" ? (
                            <CheckCircleOutlineIcon fontSize="small"
                              color={h.summary?.failed > 0 ? "warning" : "success"} />
                          ) : h.status === "FAILED" ? (
                            <ErrorOutlineIcon fontSize="small" color="error" />
                          ) : (
                            <CircularProgress size={16} />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                              <StatusChip status={h.status} />
                              {h.summary && (
                                <Typography variant="caption" color="text.secondary">
                                  {h.summary.passed}/{h.summary.total}
                                </Typography>
                              )}
                            </Box>
                          }
                          secondary={
                            <>
                              {new Date(h.started_at).toLocaleString()}
                              {h.environment_name && ` · ${h.environment_name}`}
                            </>
                          }
                        />
                        {h.status === "COMPLETED" && (
                          <Tooltip title="Open report">
                            <span>
                              <Button
                                size="small" sx={{ minWidth: 0, p: 0.5 }}
                                onClick={(e) => { e.stopPropagation(); window.open(getReportUrl(projectId, h.id), "_blank"); }}
                              >
                                <OpenInNewIcon fontSize="small" />
                              </Button>
                            </span>
                          </Tooltip>
                        )}
                      </ListItemButton>
                    );
                  })}
                </List>
              )}
            </CardContent>
          </Card>
        </Box>
      </Box>

      <EditTestCaseDialog
        open={!!editTc}
        tc={editTc}
        onClose={() => setEditTc(null)}
        onSave={handleSaveEdit}
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
    </Box>
  );
}
