import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Typography, Table, TableBody, TableCell, TableHead, TableRow,
  TablePagination, Radio, IconButton, Tooltip, Chip, CircularProgress,
  Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions, Button,
  Alert,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { listGenerations, setActiveGeneration, deleteGeneration } from "../../api/client";
import StatusChip from "../StatusChip";

const IN_PROGRESS = ["PENDING", "GENERATING", "SCENARIOS_READY", "GENERATING_STEPS"];
const PAGE_SIZE = 15;

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function GenerationsTab({ projectId, thisGenId, isAdmin, onActiveChanged, onReviewableCountChange }) {
  const [generations, setGenerations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(0);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [acting, setActing] = useState(false);
  const pollRef = useRef(null);
  const prevReviewCountRef = useRef(-1);
  const nav = useNavigate();

  const reportReviewable = useCallback((gens) => {
    const count = gens.filter((g) => g.status === "REVIEW").length;
    if (count !== prevReviewCountRef.current) {
      prevReviewCountRef.current = count;
      if (onReviewableCountChange) onReviewableCountChange(count);
    }
  }, [onReviewableCountChange]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const gens = await listGenerations(projectId);
      setGenerations(gens);
      reportReviewable(gens);
      if (gens.some((g) => IN_PROGRESS.includes(g.status)) && !pollRef.current) {
        pollRef.current = setInterval(async () => {
          try {
            const updated = await listGenerations(projectId);
            setGenerations(updated);
            reportReviewable(updated);
            if (!updated.some((g) => IN_PROGRESS.includes(g.status))) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
          } catch { /* ignore poll errors */ }
        }, 3000);
      }
    } catch {
      setError("Failed to load generations");
    } finally {
      setLoading(false);
    }
  }, [projectId, reportReviewable]);

  useEffect(() => {
    load();
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [load]);

  const handleSetActive = async (genId) => {
    setActing(true);
    try {
      await setActiveGeneration(projectId, genId);
      setGenerations((prev) => prev.map((g) => ({ ...g, is_active: g.id === genId })));
      if (onActiveChanged) onActiveChanged(genId);
    } catch {
      setError("Failed to set active generation");
    } finally {
      setActing(false);
    }
  };

  const handleDeleteConfirm = async () => {
    const genId = confirmDelete;
    setConfirmDelete(null);
    setActing(true);
    try {
      await deleteGeneration(projectId, genId);
      const updated = generations.filter((g) => g.id !== genId);
      // If the deleted gen was active, the backend promoted a new one — reload
      const wasActive = generations.find((g) => g.id === genId)?.is_active;
      if (wasActive) {
        await load();
        const reloaded = await listGenerations(projectId).catch(() => []);
        const newActive = reloaded.find((g) => g.is_active);
        if (newActive && onActiveChanged) onActiveChanged(newActive.id);
      } else {
        setGenerations(updated);
      }
    } catch {
      setError("Failed to delete generation");
    } finally {
      setActing(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (generations.length === 0) {
    return <Typography color="text.secondary" variant="body2">No generations found.</Typography>;
  }

  const paged = generations.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell padding="checkbox">Active</TableCell>
            <TableCell>Generation ID</TableCell>
            <TableCell align="right">Test Cases</TableCell>
            <TableCell>Created</TableCell>
            <TableCell>Status</TableCell>
            {isAdmin && <TableCell align="right">Delete</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {paged.map((gen) => {
            const inProgress = IN_PROGRESS.includes(gen.status);
            const isCurrent = gen.id === thisGenId;
            return (
              <TableRow
                key={gen.id}
                hover
                sx={isCurrent ? { backgroundColor: "action.selected" } : undefined}
              >
                <TableCell padding="checkbox">
                  <Radio
                    size="small"
                    checked={!!gen.is_active}
                    disabled={inProgress || acting}
                    onChange={() => handleSetActive(gen.id)}
                  />
                </TableCell>
                <TableCell
                  sx={{ fontFamily: "monospace", fontSize: 13, cursor: "pointer", "&:hover": { textDecoration: "underline" } }}
                  onClick={() => nav(`/projects/${projectId}/generations/${gen.id}`)}
                >
                  {gen.id}
                  {isCurrent && (
                    <Chip label="current view" size="small" variant="outlined" sx={{ ml: 1, fontSize: 10 }} />
                  )}
                </TableCell>
                <TableCell align="right">{gen.test_case_count ?? 0}</TableCell>
                <TableCell sx={{ whiteSpace: "nowrap" }}>{formatDate(gen.created_at)}</TableCell>
                <TableCell><StatusChip status={gen.status} /></TableCell>
                {isAdmin && (
                  <TableCell align="right">
                    <Tooltip title={inProgress ? "Cannot delete an in-progress generation" : "Delete generation"}>
                      <span>
                        <IconButton
                          size="small"
                          color="error"
                          disabled={inProgress || acting}
                          onClick={() => setConfirmDelete(gen.id)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                )}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {generations.length > PAGE_SIZE && (
        <TablePagination
          component="div"
          count={generations.length}
          page={page}
          rowsPerPage={PAGE_SIZE}
          rowsPerPageOptions={[PAGE_SIZE]}
          onPageChange={(_, p) => setPage(p)}
        />
      )}

      <Dialog open={!!confirmDelete} onClose={() => setConfirmDelete(null)}>
        <DialogTitle>Delete Generation</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Permanently delete generation <strong>{confirmDelete}</strong> and all its test cases?
            This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDelete(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={handleDeleteConfirm}>Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
