import { useEffect, useState } from "react";
import {
  Button, Dialog, DialogActions, DialogContent, TextField, CircularProgress, Alert,
  InputAdornment, IconButton,
} from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import ClosableDialogTitle from "./ClosableDialogTitle";
import { createTestUser, updateTestUser } from "../api/client";

export default function AddTestUserDialog({ open, projectId, envId, editTarget, onClose, onSaved }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rolesInput, setRolesInput] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const isEdit = !!editTarget;

  useEffect(() => {
    if (editTarget) {
      setUsername(editTarget.username);
      setPassword(editTarget.password || "");
      setRolesInput((editTarget.roles || []).join(", "));
    }
  }, [editTarget]);

  const reset = () => {
    setUsername(""); setPassword(""); setRolesInput(""); setShowPassword(false); setError("");
  };

  const handleClose = () => { reset(); onClose(); };

  const handleSave = async () => {
    if (!username.trim() || !password) {
      setError("Username and password are required");
      return;
    }
    try {
      setSaving(true);
      setError("");
      const roles = rolesInput.split(",").map((r) => r.trim()).filter(Boolean);
      const body = { username: username.trim(), password, roles };
      const updated = isEdit
        ? await updateTestUser(projectId, envId, editTarget.id, body)
        : await createTestUser(projectId, envId, body);
      reset();
      onSaved(updated);
    } catch (e) {
      setError(e.response?.data?.error || `Failed to ${isEdit ? "update" : "add"} test user`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <ClosableDialogTitle onClose={handleClose}>
        {isEdit ? "Edit Test User" : "Add Test User"}
      </ClosableDialogTitle>
      <DialogContent>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <TextField
          label="Username" fullWidth required
          value={username} onChange={(e) => setUsername(e.target.value)}
          sx={{ mb: 2, mt: 1 }}
        />
        <TextField
          label="Password" fullWidth required
          type={showPassword ? "text" : "password"}
          value={password} onChange={(e) => setPassword(e.target.value)}
          slotProps={{
            input: {
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowPassword((v) => !v)} edge="end" size="small" tabIndex={-1}>
                    {showPassword ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
                  </IconButton>
                </InputAdornment>
              ),
            },
          }}
          sx={{ mb: 2 }}
        />
        <TextField
          label="Roles" placeholder="e.g. admin, viewer, editor" fullWidth
          helperText="Comma-separated. Each value becomes a separate role."
          value={rolesInput} onChange={(e) => setRolesInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleSave(); }}
        />
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={handleClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSave} disabled={saving}>
          {saving ? <CircularProgress size={20} /> : "Save"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
