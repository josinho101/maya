import { useState } from "react";
import {
  Box, Typography, Button, Card, CardContent, CardActions,
  CircularProgress, Alert, Chip, Tooltip, TextField,
  Dialog, DialogContent, DialogActions, IconButton,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import { updateEnvironmentNames, deleteEnvironment } from "../../api/client";
import AddEnvironmentDialog from "../AddEnvironmentDialog";
import ClosableDialogTitle from "../ClosableDialogTitle";

export default function EnvironmentsTab({ environments, projectId, isAdmin, onEnvCreated, onRefreshEnvironments }) {
  const [addEnvOpen, setAddEnvOpen] = useState(false);
  const [envEditTarget, setEnvEditTarget] = useState(null);
  const [envNameInput, setEnvNameInput] = useState("");
  const [envSaving, setEnvSaving] = useState(false);
  const [envDeleteTarget, setEnvDeleteTarget] = useState(null);
  const [envDeleting, setEnvDeleting] = useState(false);
  const [error, setError] = useState("");

  const handleOpenEnvEdit = (env) => {
    setEnvEditTarget(env);
    setEnvNameInput(env.name);
  };

  const handleEnvRename = async () => {
    if (!envNameInput.trim()) return;
    try {
      setEnvSaving(true);
      await updateEnvironmentNames(projectId, [{ id: envEditTarget.id, name: envNameInput.trim() }]);
      await onRefreshEnvironments();
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
      await onRefreshEnvironments();
      setEnvDeleteTarget(null);
    } catch (e) {
      setError(e.response?.data?.error || "Failed to delete environment");
    } finally {
      setEnvDeleting(false);
    }
  };

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
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

      <AddEnvironmentDialog
        open={addEnvOpen}
        projectId={projectId}
        onClose={() => setAddEnvOpen(false)}
        onCreated={(createdList) => { setAddEnvOpen(false); onEnvCreated(createdList); }}
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
