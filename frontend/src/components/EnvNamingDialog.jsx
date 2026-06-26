import { useState, useEffect } from "react";
import {
  Box, Button, Dialog, DialogActions, DialogContent, TextField,
  Typography, CircularProgress, Alert,
} from "@mui/material";
import LanguageIcon from "@mui/icons-material/Language";
import ClosableDialogTitle from "./ClosableDialogTitle";
import { updateEnvironmentNames } from "../api/client";

export default function EnvNamingDialog({ open, projectId, environments, onClose, onSaved }) {
  const [names, setNames] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (environments?.length) {
      const initial = {};
      environments.forEach((e) => { initial[e.id] = e.name; });
      setNames(initial);
    }
  }, [environments]);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError("");
      await updateEnvironmentNames(
        projectId,
        environments.map((e) => ({ id: e.id, name: names[e.id] }))
      );
      onSaved();
    } catch (e) {
      setError(e.response?.data?.error || "Failed to save environment names");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <ClosableDialogTitle onClose={onClose} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <LanguageIcon color="primary" />
        Name Your Environments
      </ClosableDialogTitle>
      <DialogContent>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          This API spec declares the servers below. Give each one a name (e.g. Dev, QA, Prod) -
          you can rename these later from the Environments tab.
        </Typography>
        {(environments || []).map((env) => (
          <Box key={env.id} sx={{ mb: 2 }}>
            <TextField
              label="Name"
              fullWidth
              size="small"
              value={names[env.id] || ""}
              onChange={(e) => setNames({ ...names, [env.id]: e.target.value })}
              sx={{ mb: 0.5 }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ fontFamily: "monospace" }}>
              {env.url}
            </Typography>
          </Box>
        ))}
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={onClose}>Skip</Button>
        <Button variant="contained" onClick={handleSave} disabled={saving}>
          {saving ? <CircularProgress size={20} /> : "Save"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
