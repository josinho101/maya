import { useState, useEffect, useCallback, useRef } from "react";
import {
  Box, Typography, Button, Card, CardContent, CircularProgress, Alert,
  Accordion, AccordionSummary, AccordionDetails, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, LinearProgress, Chip, Tooltip,
  TextField, InputAdornment, Dialog, DialogTitle, DialogContent, DialogActions,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import { useNavigate, useParams } from "react-router-dom";
import {
  getGeneration, editTestCase, deleteTestCase, approveGeneration,
  executeGeneration, triggerGeneration,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusChip from "../components/StatusChip";
import EditTestCaseDialog from "../components/EditTestCaseDialog";

const POLLING_STATUSES = ["PENDING", "GENERATING"];
const LIFECYCLE_ROLE_COLOR = {
  create: "success", read: "info", update: "warning", delete: "error",
  verify_create: "secondary", verify_update: "secondary", verify_delete: "secondary",
};

export default function GenerationPage() {
  const { projectId, genId } = useParams();
  const nav = useNavigate();
  const pollRef = useRef(null);
  const { isAdmin } = useAuth();

  const [gen, setGen] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editTc, setEditTc] = useState(null);
  const [deleteTc, setDeleteTc] = useState(null);
  const [approving, setApproving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [tcSearch, setTcSearch] = useState("");

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
      const res = await executeGeneration(projectId, genId);
      nav(`/projects/${projectId}/executions/${res.execution_id}`);
    } catch (e) {
      setError(e.response?.data?.error || "Execute failed");
      setExecuting(false);
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
  const progress = gen?.progress;

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={() => nav(`/projects/${projectId}`)} sx={{ mb: 2 }}>
        Project
      </Button>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <Typography variant="h5" fontWeight={700} sx={{ flex: 1 }}>Generation</Typography>
        <Chip label={`ID: ${genId}`} size="small" sx={{ fontFamily: "monospace" }} />
        {gen && <StatusChip status={gen.status} size="medium" />}
      </Box>

      {/* Polling state */}
      {gen && POLLING_STATUSES.includes(gen.status) && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography fontWeight={600} gutterBottom>
              {gen.status === "PENDING" ? "Queued..." : "Generating test cases....."}
            </Typography>
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

      {/* Review / Approved — test cases */}
      {gen && (gen.status === "REVIEW" || gen.status === "APPROVED") && (
        <>
          <Box sx={{ display: "flex", gap: 2, mb: 3, alignItems: "center", flexWrap: "wrap" }}>
            <Typography color="text.secondary">
              {totalTc} test cases across {results.length} endpoints
            </Typography>
            <Box sx={{ ml: "auto", display: "flex", gap: 1, alignItems: "center" }}>
              {totalTc > 0 && (
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
              {gen.status === "REVIEW" && isAdmin && (
                <Button
                  variant="contained"
                  color="success"
                  startIcon={approving ? <CircularProgress size={16} /> : <CheckCircleIcon />}
                  onClick={handleApprove}
                  disabled={approving}
                >
                  Approve
                </Button>
              )}
              {gen.status === "APPROVED" && (
                <Button
                  variant="contained"
                  startIcon={executing ? <CircularProgress size={16} /> : <PlayArrowIcon />}
                  onClick={handleExecute}
                  disabled={executing}
                >
                  Run Tests
                </Button>
              )}
            </Box>
          </Box>

          {results.map((result, idx) => {
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
              <Accordion key={idx} defaultExpanded={idx === 0} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Chip
                      label={result.method || "?"}
                      size="small"
                      color={
                        result.method === "GET" ? "info" :
                        result.method === "POST" ? "success" :
                        result.method === "DELETE" ? "error" : "default"
                      }
                    />
                    <Typography fontFamily="monospace" fontSize={14}>{result.endpoint}</Typography>
                    <Chip label={`${result.test_cases?.length || 0} cases`} size="small" variant="outlined" />
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
        </>
      )}

      <EditTestCaseDialog
        open={!!editTc}
        tc={editTc}
        onClose={() => setEditTc(null)}
        onSave={handleSave}
      />

      <Dialog open={!!deleteTc} onClose={() => setDeleteTc(null)}>
        <DialogTitle>Delete Test Case</DialogTitle>
        <DialogContent>
          <Typography>Delete <strong>{deleteTc?.tc_id}</strong>? This cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTc(null)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
