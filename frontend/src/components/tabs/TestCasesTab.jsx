import { useState, useCallback, useMemo, useDeferredValue, memo } from "react";
import {
  Box, Typography, Button, CircularProgress, Alert,
  Accordion, AccordionSummary, AccordionDetails, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, Chip, Tooltip,
  TextField, InputAdornment, Dialog, DialogContent, DialogActions,
  Select, MenuItem, Badge,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SearchIcon from "@mui/icons-material/Search";
import LockIcon from "@mui/icons-material/Lock";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import AddIcon from "@mui/icons-material/Add";
import { useNavigate } from "react-router-dom";
import {
  approveGeneration, approveTestCase, executeGeneration,
  editTestCase, deleteTestCase, addTestCase,
} from "../../api/client";
import EditTestCaseDialog from "../EditTestCaseDialog";
import ClosableDialogTitle from "../ClosableDialogTitle";
import Toast from "../Toast";

const METHOD_COLOR = { GET: "info", POST: "success", PUT: "warning", PATCH: "warning", DELETE: "error" };
const LIFECYCLE_ROLE_COLOR = {
  create: "success", read: "info", update: "warning", delete: "error",
  verify_create: "secondary", verify_update: "secondary", verify_delete: "secondary",
};

const TestCaseRow = memo(function TestCaseRow({
  tc, endpoint, method, requiresAuth,
  selectedEnvId, tableTestUsers, isAdmin,
  isStepsExpanded, isDuplicating,
  onToggleSteps, onApprove, onTcTestUserChange, onEdit, onDuplicate, onDelete,
}) {
  return (
    <TableRow hover>
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
            <IconButton size="small" onClick={() => onToggleSteps(tc.tc_id)}>
              {isStepsExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </IconButton>
          </Box>
          {isStepsExpanded && !tc.steps_error && (
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
      {requiresAuth && (
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
              onChange={(e) => onTcTestUserChange(tc, selectedEnvId, e.target.value)}
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
                <IconButton size="small" color="success" onClick={() => onApprove(tc.tc_id)}>
                  <CheckCircleIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            <Tooltip title="Edit test case">
              <IconButton size="small" onClick={() => onEdit(tc, endpoint, method, requiresAuth)}>
                <EditIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Duplicate test case">
              <IconButton
                size="small"
                onClick={() => onDuplicate(tc, endpoint, method)}
                disabled={isDuplicating}
              >
                {isDuplicating ? <CircularProgress size={16} /> : <ContentCopyIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete test case">
              <IconButton size="small" color="error" onClick={() => onDelete(tc)}>
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        )}
      </TableCell>
    </TableRow>
  );
});

const EndpointAccordion = memo(function EndpointAccordion({
  result, filteredCases,
  selectedEnvId, tableTestUsers, isAdmin,
  expandedSteps, duplicatingTcs,
  onToggleSteps, onApprove, onTcTestUserChange, onEdit, onDuplicate, onDelete,
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <Accordion sx={{ mb: 1 }} expanded={expanded} onChange={(_, v) => setExpanded(v)}>
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
        {expanded && (result.error ? (
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
                <TestCaseRow
                  key={tc.tc_id}
                  tc={tc}
                  endpoint={result.endpoint}
                  method={result.method}
                  requiresAuth={result.requires_auth}
                  selectedEnvId={selectedEnvId}
                  tableTestUsers={tableTestUsers}
                  isAdmin={isAdmin}
                  isStepsExpanded={expandedSteps.has(tc.tc_id)}
                  isDuplicating={duplicatingTcs.has(tc.tc_id)}
                  onToggleSteps={onToggleSteps}
                  onApprove={onApprove}
                  onTcTestUserChange={onTcTestUserChange}
                  onEdit={onEdit}
                  onDuplicate={onDuplicate}
                  onDelete={onDelete}
                />
              ))}
            </TableBody>
          </Table>
        ))}
      </AccordionDetails>
    </Accordion>
  );
});

export default function TestCasesTab({
  gen, genId, projectId, isAdmin, mainTab,
  environments, selectedEnvId, onSelectedEnvIdChange, tableTestUsers,
  onFetchGen, onSwitchToEnvironments,
}) {
  const nav = useNavigate();

  const [editTarget, setEditTarget] = useState(null);
  const [deleteTc, setDeleteTc] = useState(null);
  const [approving, setApproving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [tcSearch, setTcSearch] = useState("");
  const deferredTcSearch = useDeferredValue(tcSearch);
  const [expandedSteps, setExpandedSteps] = useState(new Set());
  const [duplicatingTcs, setDuplicatingTcs] = useState(new Set());
  const [toast, setToast] = useState({ open: false, message: "" });
  const [error, setError] = useState("");

  const results = gen?.testcases?.results || [];
  const needsReviewCount = results.reduce(
    (n, r) => n + (r.test_cases || []).filter((tc) => tc.needs_review).length, 0
  );
  const totalTc = results.reduce((n, r) => n + (r.test_cases?.length || 0), 0);
  const approvedTc = totalTc - needsReviewCount;

  const filteredResultCases = useMemo(() => {
    const q = deferredTcSearch.trim().toLowerCase();
    return results
      .map((result) => ({
        result,
        filteredCases: (result.test_cases || []).filter((tc) => {
          if (mainTab === "needs_review" && !tc.needs_review) return false;
          if (mainTab === "all" && tc.needs_review) return false;
          if (!q) return true;
          return tc.tc_id?.toLowerCase().includes(q) || tc.test_scenario?.toLowerCase().includes(q);
        }),
      }))
      .filter(({ filteredCases }) => filteredCases.length > 0);
  }, [results, deferredTcSearch, mainTab]);

  const handleApprove = async () => {
    try {
      setApproving(true);
      await approveGeneration(projectId, genId);
      onFetchGen();
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

  const handleApproveTestCase = useCallback(async (tcId) => {
    try {
      await approveTestCase(projectId, genId, tcId);
      await onFetchGen();
    } catch (e) {
      setError(e.response?.data?.error || "Approve failed");
    }
  }, [projectId, genId, onFetchGen]);

  const handleTcTestUserChange = useCallback(async (tc, envId, userId) => {
    const assignments = { ...(tc.test_user_assignments || {}) };
    if (userId) assignments[envId] = userId;
    else delete assignments[envId];
    await editTestCase(projectId, genId, tc.tc_id, { ...tc, test_user_assignments: assignments });
    await onFetchGen();
    setToast({ open: true, message: "Test user assignment saved" });
  }, [projectId, genId, onFetchGen]);

  const handleDuplicate = useCallback(async (tc, endpoint, method) => {
    setDuplicatingTcs((prev) => new Set(prev).add(tc.tc_id));
    try {
      const { tc_id, source, needs_review, ...rest } = tc;
      await addTestCase(projectId, genId, {
        ...rest,
        test_scenario: `${tc.test_scenario} (Duplicate)`,
        endpoint,
        method,
      });
      await onFetchGen();
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
  }, [projectId, genId, onFetchGen]);

  const handleOpenEdit = useCallback((tc, endpoint, method, requiresAuth) => {
    setEditTarget({ tc, endpoint, method, requiresAuth });
  }, []);

  const handleOpenDelete = useCallback((tc) => {
    setDeleteTc(tc);
  }, []);

  const handleSave = async (updated) => {
    await editTestCase(projectId, genId, updated.tc_id, updated);
    await onFetchGen();
  };

  const handleDelete = async () => {
    await deleteTestCase(projectId, genId, deleteTc.tc_id);
    setDeleteTc(null);
    await onFetchGen();
  };

  const toggleStepsExpanded = useCallback((tcId) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(tcId)) next.delete(tcId); else next.add(tcId);
      return next;
    });
  }, []);

  return (
    <>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

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
            {approvedTc > 0 && environments.length > 0 && (
              <Select
                size="small"
                value={selectedEnvId}
                onChange={(e) => onSelectedEnvIdChange(e.target.value)}
                sx={{ minWidth: 160 }}
              >
                {environments.map((env) => (
                  <MenuItem key={env.id} value={env.id}>{env.name}</MenuItem>
                ))}
              </Select>
            )}
            {gen.status === "APPROVED" && environments.length === 0 && (
              <Button variant="outlined" startIcon={<AddIcon />} onClick={onSwitchToEnvironments}>
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

      {filteredResultCases.map(({ result, filteredCases }) => (
        <EndpointAccordion
          key={result.endpoint + result.method}
          result={result}
          filteredCases={filteredCases}
          selectedEnvId={selectedEnvId}
          tableTestUsers={tableTestUsers}
          isAdmin={isAdmin}
          expandedSteps={expandedSteps}
          duplicatingTcs={duplicatingTcs}
          onToggleSteps={toggleStepsExpanded}
          onApprove={handleApproveTestCase}
          onTcTestUserChange={handleTcTestUserChange}
          onEdit={handleOpenEdit}
          onDuplicate={handleDuplicate}
          onDelete={handleOpenDelete}
        />
      ))}

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

      <Toast
        open={toast.open}
        message={toast.message}
        onClose={() => setToast((t) => ({ ...t, open: false }))}
      />
    </>
  );
}
