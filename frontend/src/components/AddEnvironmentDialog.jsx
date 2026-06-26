import { useState } from "react";
import {
  Button, Dialog, DialogActions, DialogContent, TextField, CircularProgress, Alert,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ClosableDialogTitle from "./ClosableDialogTitle";
import { createEnvironment } from "../api/client";

export default function AddEnvironmentDialog({ open, projectId, title, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const reset = () => { setName(""); setUrl(""); setError(""); };

  const handleClose = () => { reset(); onClose(); };

  const handleCreate = async () => {
    if (!name.trim() || !url.trim()) { setError("Name and URL are required"); return; }
    try {
      setSaving(true);
      setError("");
      const updated = await createEnvironment(projectId, { name: name.trim(), url: url.trim() });
      reset();
      onCreated(updated);
    } catch (e) {
      setError(e.response?.data?.error || "Failed to add environment");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <ClosableDialogTitle onClose={handleClose} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <AddIcon color="primary" />
        {title || "Add Environment"}
      </ClosableDialogTitle>
      <DialogContent>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <TextField
          label="Name" placeholder="e.g. Dev, QA, Local" fullWidth required
          value={name} onChange={(e) => setName(e.target.value)}
          sx={{ mb: 2, mt: 1 }}
        />
        <TextField
          label="URL" placeholder="https://api.example.com" fullWidth required
          value={url} onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
        />
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={handleClose}>Cancel</Button>
        <Button variant="contained" onClick={handleCreate} disabled={saving}>
          {saving ? <CircularProgress size={20} /> : "Create"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
