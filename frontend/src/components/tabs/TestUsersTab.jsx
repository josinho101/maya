import { useState, useEffect, useCallback } from "react";
import {
  Box, Typography, Button, CircularProgress, Alert,
  Table, TableBody, TableCell, TableHead, TableRow,
  IconButton, Chip, Tooltip, Dialog, DialogContent, DialogActions,
  Select, MenuItem,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import { listTestUsers, deleteTestUser } from "../../api/client";
import AddTestUserDialog from "../AddTestUserDialog";
import ClosableDialogTitle from "../ClosableDialogTitle";

export default function TestUsersTab({ environments, projectId, isAdmin }) {
  const [tuSelectedEnvId, setTuSelectedEnvId] = useState("");
  const [testUsers, setTestUsers] = useState([]);
  const [tuLoading, setTuLoading] = useState(false);
  const [revealedTu, setRevealedTu] = useState(new Set());
  const [addTuOpen, setAddTuOpen] = useState(false);
  const [editTuTarget, setEditTuTarget] = useState(null);
  const [deleteTuTarget, setDeleteTuTarget] = useState(null);
  const [tuDeleting, setTuDeleting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setTuSelectedEnvId((prev) => (environments.some((e) => e.id === prev) ? prev : environments[0]?.id || ""));
  }, [environments]);

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
    setRevealedTu(new Set());
    fetchTestUsers(tuSelectedEnvId);
  }, [tuSelectedEnvId, fetchTestUsers]);

  const toggleReveal = (id) => {
    setRevealedTu((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleTuSaved = (updated) => {
    setAddTuOpen(false);
    setEditTuTarget(null);
    setTestUsers(updated);
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

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
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
    </Box>
  );
}
