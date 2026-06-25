import { useState } from "react";
import { Box, Typography, Button, TextField } from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { uploadTestcaseFile } from "../api/client";

// Shared by AddTestCaseDialog and EditTestCaseDialog: lets the user attach a
// real uploaded file to a test case's `files` entries, instead of typing a
// fake path into a JSON blob. Files are uploaded immediately on selection and
// stored under the project's own output dir (see backend upload-file route).
export default function FileFieldEditor({ projectId, genId, files, fileFields, acceptsFile, onChange }) {
  const [newFieldName, setNewFieldName] = useState("");
  const [uploadingField, setUploadingField] = useState(null);
  const [err, setErr] = useState("");

  const knownFields = Array.from(new Set([...(fileFields || []), ...Object.keys(files || {})]));

  const handleUpload = async (fieldName, file) => {
    if (!file) return;
    try {
      setUploadingField(fieldName);
      setErr("");
      const { path } = await uploadTestcaseFile(projectId, genId, file);
      onChange({ ...files, [fieldName]: path });
    } catch (e) {
      setErr(e.response?.data?.error || "Upload failed");
    } finally {
      setUploadingField(null);
    }
  };

  if (!acceptsFile && knownFields.length === 0) return null;

  return (
    <Box sx={{ mb: 2, p: 1.5, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
        File fields
      </Typography>
      {err && (
        <Typography variant="caption" color="error" sx={{ display: "block", mb: 1 }}>
          {err}
        </Typography>
      )}
      {knownFields.map((name) => (
        <Box key={name} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <Typography variant="body2" sx={{ width: 120, fontFamily: "monospace" }}>
            {name}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ flex: 1, overflowWrap: "anywhere" }}>
            {files?.[name] || "(no file selected)"}
          </Typography>
          <Button
            size="small"
            component="label"
            startIcon={<UploadFileIcon fontSize="small" />}
            disabled={uploadingField === name}
          >
            {files?.[name] ? "Replace" : "Choose file"}
            <input type="file" hidden onChange={(e) => handleUpload(name, e.target.files[0])} />
          </Button>
        </Box>
      ))}
      {acceptsFile && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1 }}>
          <TextField
            size="small"
            placeholder="New file field name"
            value={newFieldName}
            onChange={(e) => setNewFieldName(e.target.value)}
            sx={{ width: 200 }}
          />
          <Button
            size="small"
            component="label"
            disabled={!newFieldName.trim()}
            startIcon={<UploadFileIcon fontSize="small" />}
          >
            Add file field
            <input
              type="file"
              hidden
              onChange={(e) => {
                const file = e.target.files[0];
                const name = newFieldName.trim();
                if (file && name) {
                  handleUpload(name, file);
                  setNewFieldName("");
                }
              }}
            />
          </Button>
        </Box>
      )}
    </Box>
  );
}
