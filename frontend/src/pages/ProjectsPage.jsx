import { useState, useEffect, useCallback } from "react";
import {
  Box, Card, CardContent, CardActions, Typography, Button, Fab,
  Dialog, DialogContent, DialogActions, TextField,
  IconButton, CircularProgress, Alert, Tooltip, Chip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import FolderIcon from "@mui/icons-material/Folder";
import { useNavigate } from "react-router-dom";
import { getProjects, createProject, updateProject, deleteProject, listGenerations } from "../api/client";
import { useAuth } from "../context/AuthContext";
import ClosableDialogTitle from "../components/ClosableDialogTitle";

export default function ProjectsPage() {
  const nav = useNavigate();
  const { isAdmin } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [editTarget, setEditTarget] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", description: "" });
  const [editError, setEditError] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  const [generatingMap, setGeneratingMap] = useState({});

  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      const projs = await getProjects();
      setProjects(projs);
      const statuses = await Promise.all(
        projs.map(async (p) => {
          try {
            const gens = await listGenerations(p.id);
            return { id: p.id, active: gens.some((g) => ["PENDING", "GENERATING", "SCENARIOS_READY", "GENERATING_STEPS"].includes(g.status)) };
          } catch {
            return { id: p.id, active: false };
          }
        })
      );
      const map = {};
      statuses.forEach((s) => { map[s.id] = s.active; });
      setGeneratingMap(map);
    } catch {
      setError("Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const handleCreate = async () => {
    if (!form.name.trim()) { setFormError("Name is required"); return; }
    try {
      setSaving(true);
      await createProject(form);
      setCreateOpen(false);
      setForm({ name: "", description: "" });
      setFormError("");
      fetchProjects();
    } catch (e) {
      setFormError(e.response?.data?.error || "Failed to create project");
    } finally {
      setSaving(false);
    }
  };

  const handleEditSave = async () => {
    if (!editForm.name.trim()) { setEditError("Name is required"); return; }
    try {
      setEditSaving(true);
      setEditError("");
      await updateProject(editTarget.id, { name: editForm.name.trim(), description: editForm.description.trim() });
      await fetchProjects();
      setEditTarget(null);
    } catch (e) {
      setEditError(e.response?.data?.error || "Failed to save");
    } finally {
      setEditSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await deleteProject(deleteTarget.id);
      setDeleteTarget(null);
      fetchProjects();
    } catch {
      setError("Failed to delete project");
    }
  };

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", mb: 3 }}>
        <Typography variant="h5" fontWeight={700} sx={{ flex: 1 }}>Projects</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {projects.length === 0 ? (
        <Box sx={{ textAlign: "center", mt: 10, color: "text.secondary" }}>
          <FolderIcon sx={{ fontSize: 64, mb: 2, opacity: 0.3 }} />
          <Typography>No projects yet. Create one to get started.</Typography>
        </Box>
      ) : (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
          {projects.map((p) => (
              <Card key={p.id} sx={{ width: 280, height: 210, flex: "0 0 280px", display: "flex", flexDirection: "column", position: "relative" }}>
                {generatingMap[p.id] && (
                  <Chip
                    size="small"
                    icon={<CircularProgress size={10} sx={{ color: "inherit !important" }} />}
                    label="Generating..."
                    color="warning"
                    sx={{ position: "absolute", top: 10, right: 10, fontSize: 11, height: 22 }}
                  />
                )}
                <CardContent sx={{ flex: 1, overflow: "hidden" }}>
                  <Typography variant="h6" fontWeight={600} gutterBottom noWrap>{p.name}</Typography>
                  <Tooltip title={p.description || ""} arrow placement="top">
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        mb: 1,
                        display: "-webkit-box",
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                        cursor: "default",
                      }}
                    >
                      {p.description || "No description"}
                    </Typography>
                  </Tooltip>
                  <Typography variant="caption" color="text.secondary">
                    Created {new Date(p.created_at).toLocaleDateString()}
                  </Typography>
                </CardContent>
                <CardActions sx={{ px: 2, pb: 2, pt: 0 }}>
                  <Button
                    size="small"
                    variant="contained"
                    endIcon={<ArrowForwardIcon />}
                    onClick={() => nav(`/projects/${p.id}`)}
                    sx={{ mr: "auto" }}
                  >
                    Open
                  </Button>
                  {isAdmin && (
                    <Tooltip title="Edit project">
                      <IconButton size="small" onClick={() => { setEditTarget(p); setEditForm({ name: p.name, description: p.description || "" }); setEditError(""); }}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                  {isAdmin && (
                    <Tooltip title="Delete project">
                      <IconButton size="small" color="error" onClick={() => setDeleteTarget(p)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </CardActions>
              </Card>
          ))}
        </Box>
      )}

      {isAdmin && (
        <Fab
          color="primary"
          onClick={() => setCreateOpen(true)}
          sx={{ position: "fixed", bottom: 32, right: 32 }}
        >
          <AddIcon />
        </Fab>
      )}

      {/* Create dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <ClosableDialogTitle onClose={() => setCreateOpen(false)}>New Project</ClosableDialogTitle>
        <DialogContent>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
          <TextField
            label="Project Name" fullWidth required sx={{ mb: 2, mt: 1 }}
            value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <TextField
            label="Description" fullWidth multiline rows={2}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => { setCreateOpen(false); setFormError(""); }}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={saving}>
            {saving ? <CircularProgress size={20} /> : "Create"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={!!editTarget} onClose={() => setEditTarget(null)} maxWidth="sm" fullWidth>
        <ClosableDialogTitle onClose={() => setEditTarget(null)}>Edit Project</ClosableDialogTitle>
        <DialogContent>
          {editError && <Alert severity="error" sx={{ mb: 2 }}>{editError}</Alert>}
          <TextField
            label="Project Name" fullWidth required sx={{ mb: 2, mt: 1 }}
            value={editForm.name}
            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
            onKeyDown={(e) => e.key === "Enter" && handleEditSave()}
          />
          <TextField
            label="Description" fullWidth multiline rows={2}
            value={editForm.description}
            onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => setEditTarget(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleEditSave} disabled={editSaving}>
            {editSaving ? <CircularProgress size={20} /> : "Save"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete confirm dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} maxWidth="xs" fullWidth>
        <ClosableDialogTitle onClose={() => setDeleteTarget(null)}>Delete Project</ClosableDialogTitle>
        <DialogContent>
          <Typography>
            Delete <strong>{deleteTarget?.name}</strong>? This removes all swagger uploads,
            generated test cases, and execution reports.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
