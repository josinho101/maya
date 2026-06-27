import { useState, useEffect } from "react";
import {
  Box, Button, CircularProgress, Alert, Dialog,
  DialogContent, DialogActions, TextField, Chip, Typography,
} from "@mui/material";
import FileFieldEditor from "./FileFieldEditor";
import ClosableDialogTitle from "./ClosableDialogTitle";
import { getTestcaseSample } from "../api/client";

const LIFECYCLE_ROLE_COLOR = {
  create: "success", read: "info", update: "warning", delete: "error",
  verify_create: "secondary", verify_update: "secondary", verify_delete: "secondary",
};

export function JsonField({ label, value, onChange }) {
  const [raw, setRaw] = useState(typeof value === "string" ? value : JSON.stringify(value, null, 2));
  const [err, setErr] = useState("");
  const handleChange = (v) => {
    setRaw(v);
    try { JSON.parse(v); setErr(""); onChange(JSON.parse(v)); }
    catch { setErr("Invalid JSON"); }
  };
  return (
    <Box sx={{ mb: 2 }}>
      <TextField
        label={label} fullWidth multiline minRows={3}
        value={raw} onChange={(e) => handleChange(e.target.value)}
        error={!!err} helperText={err}
        inputProps={{ style: { fontFamily: "monospace", fontSize: 13 } }}
      />
    </Box>
  );
}

export function StepsField({ label, value, onChange }) {
  const [raw, setRaw] = useState((value || []).join("\n"));
  const handleChange = (v) => {
    setRaw(v);
    const steps = v.split("\n");
    while (steps.length && steps[steps.length - 1].trim() === "") steps.pop();
    onChange(steps);
  };
  return (
    <Box sx={{ mb: 2 }}>
      <TextField
        label={label} fullWidth multiline minRows={3}
        value={raw} onChange={(e) => handleChange(e.target.value)}
        helperText="One step per line"
        inputProps={{ style: { fontFamily: "monospace", fontSize: 13 } }}
      />
    </Box>
  );
}

export default function EditTestCaseDialog({ open, tc, endpoint, method, projectId, genId, onClose, onSave }) {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [fileFields, setFileFields] = useState([]);
  const [acceptsFile, setAcceptsFile] = useState(false);

  useEffect(() => {
    if (tc) setForm(JSON.parse(JSON.stringify(tc)));
  }, [tc]);

  useEffect(() => {
    if (!tc || !endpoint || !method) return;
    // Only file_fields/accepts_file are used here - the sample itself is
    // ignored so opening Edit never overwrites the test case's real values.
    getTestcaseSample(projectId, genId, endpoint, method)
      .then(({ file_fields, accepts_file }) => {
        setFileFields(file_fields || []);
        setAcceptsFile(accepts_file);
      })
      .catch(() => {
        setFileFields([]);
        setAcceptsFile(false);
      });
  }, [tc, endpoint, method, projectId, genId]);

  const handleSave = async () => {
    try {
      setSaving(true);
      await onSave(form);
      onClose();
    } catch (e) {
      setErr(e.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (!form) return null;
  if (tc && form.tc_id !== tc.tc_id) return null;
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <ClosableDialogTitle onClose={onClose} sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        Edit Test Case — {form.tc_id}
        <Chip
          label={form.lifecycle_role || "independent"}
          size="small"
          color={LIFECYCLE_ROLE_COLOR[form.lifecycle_role] || "default"}
        />
      </ClosableDialogTitle>
      <DialogContent>
        {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}
        <TextField
          label="Test Scenario" fullWidth sx={{ mb: 2, mt: 1 }}
          value={form.test_scenario || ""}
          onChange={(e) => setForm({ ...form, test_scenario: e.target.value })}
        />
        <JsonField label="Path Params" value={form.path_params || {}}
          onChange={(v) => setForm({ ...form, path_params: v })} />
        <JsonField label="Query Params" value={form.query_params || {}}
          onChange={(v) => setForm({ ...form, query_params: v })} />
        <JsonField label="Headers" value={form.headers || {}}
          onChange={(v) => setForm({ ...form, headers: v })} />
        <JsonField label="Request Data" value={form.request_data || {}}
          onChange={(v) => setForm({ ...form, request_data: v })} />
        <FileFieldEditor
          projectId={projectId} genId={genId}
          files={form.files || {}} fileFields={fileFields} acceptsFile={acceptsFile}
          onChange={(files) => setForm({ ...form, files })}
        />
        <JsonField label="Expected Response" value={form.expected_response || {}}
          onChange={(v) => setForm({ ...form, expected_response: v })} />
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Test Steps
            </Typography>
            {form.steps_error && (
              <Chip label="steps generation failed" size="small" color="warning" variant="outlined" />
            )}
          </Box>
          <StepsField label="Steps" value={form.steps || []}
            onChange={(steps) => setForm({ ...form, steps })} />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSave} disabled={saving}>
          {saving ? <CircularProgress size={20} /> : "Save"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
