import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogActions, Button,
  List, ListItemButton, ListItemText, CircularProgress, Alert, Typography,
} from "@mui/material";
import { listTestcaseFiles } from "../api/client";
import ClosableDialogTitle from "./ClosableDialogTitle";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Lets the user pick a file previously uploaded for this project instead of
// re-uploading the same file for every test case that needs it.
export default function FileLibraryDialog({ open, projectId, genId, onClose, onSelect }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setErr("");
    listTestcaseFiles(projectId, genId)
      .then(setFiles)
      .catch((e) => setErr(e.response?.data?.error || "Failed to load files"))
      .finally(() => setLoading(false));
  }, [open, projectId, genId]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <ClosableDialogTitle onClose={onClose}>Select an uploaded file</ClosableDialogTitle>
      <DialogContent>
        {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}
        {loading && (
          <CircularProgress size={24} />
        )}
        {!loading && !err && files.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No files have been uploaded for this project yet.
          </Typography>
        )}
        {!loading && files.length > 0 && (
          <List dense sx={{ maxHeight: 5 * 64, overflowY: "auto" }}>
            {files.map((f) => (
              <ListItemButton key={f.path} onClick={() => onSelect(f.path)}>
                <ListItemText
                  primary={f.name}
                  secondary={`${formatSize(f.size)} - uploaded ${new Date(f.uploaded_at).toLocaleString()}`}
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={onClose}>Cancel</Button>
      </DialogActions>
    </Dialog>
  );
}
