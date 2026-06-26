import { useState } from "react";
import { Box, Typography, Button, TextField, Checkbox, FormControlLabel } from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import { uploadTestcaseFile } from "../api/client";
import FileLibraryDialog from "./FileLibraryDialog";

// Server-side filesystem paths must never be shown verbatim in the UI (they
// reveal server directory structure) - only the filename is displayed.
const basename = (path) => (path ? path.split(/[\\/]/).pop() : path);

// Shared by AddTestCaseDialog and EditTestCaseDialog: lets the user attach a
// real uploaded file to a test case's `files` entries, instead of typing a
// fake path into a JSON blob. Files are uploaded immediately on selection and
// stored under the project's own output dir (see backend upload-file route),
// or picked from files already uploaded earlier via the file library so the
// same file doesn't have to be re-uploaded for every test case that needs it.
export default function FileFieldEditor({ projectId, genId, files, fileFields, acceptsFile, onChange }) {
  const [newFieldName, setNewFieldName] = useState("");
  const [uploadingField, setUploadingField] = useState(null);
  const [libraryField, setLibraryField] = useState(null);
  // Fields the user has unchecked to simulate "this request didn't include
  // the file" - excluding a field just drops its key from `files`, which is
  // already what the backend treats as "no file" (FileManager skips missing
  // keys), so no separate opt-out flag needs to be persisted on the test case.
  const [excludedFields, setExcludedFields] = useState(new Set());
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

  const handleSelectFromLibrary = (path) => {
    onChange({ ...files, [libraryField]: path });
    setLibraryField(null);
  };

  const handleToggleInclude = (fieldName, included) => {
    const next = new Set(excludedFields);
    if (included) {
      next.delete(fieldName);
    } else {
      next.add(fieldName);
      const { [fieldName]: _omit, ...rest } = files || {};
      onChange(rest);
    }
    setExcludedFields(next);
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
      {knownFields.map((name) => {
        const included = !excludedFields.has(name);
        return (
          <Box key={name} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
            <FormControlLabel
              sx={{ m: 0 }}
              control={
                <Checkbox
                  size="small"
                  checked={included}
                  onChange={(e) => handleToggleInclude(name, e.target.checked)}
                />
              }
              label={
                <Typography variant="body2" sx={{ width: 120, fontFamily: "monospace" }}>
                  {name}
                </Typography>
              }
            />
            <Typography variant="caption" color="text.secondary" sx={{ flex: 1, overflowWrap: "anywhere" }}>
              {included ? basename(files?.[name]) || "(no file selected)" : "(excluded - simulating no file)"}
            </Typography>
            {included && (
              <>
                <Button
                  size="small"
                  component="label"
                  startIcon={<UploadFileIcon fontSize="small" />}
                  disabled={uploadingField === name}
                >
                  {files?.[name] ? "Replace" : "Choose file"}
                  <input type="file" hidden onChange={(e) => handleUpload(name, e.target.files[0])} />
                </Button>
                <Button
                  size="small"
                  startIcon={<FolderOpenIcon fontSize="small" />}
                  onClick={() => setLibraryField(name)}
                >
                  Browse Library
                </Button>
              </>
            )}
          </Box>
        );
      })}
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
      <FileLibraryDialog
        open={!!libraryField}
        projectId={projectId}
        genId={genId}
        onClose={() => setLibraryField(null)}
        onSelect={handleSelectFromLibrary}
      />
    </Box>
  );
}
