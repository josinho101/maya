import { useState } from "react";
import {
  Box, Button, CircularProgress, Alert, Dialog,
  DialogContent, DialogActions, TextField, MenuItem, Tabs, Tab,
} from "@mui/material";
import { JsonField, StepsField } from "./EditTestCaseDialog";
import FileFieldEditor from "./FileFieldEditor";
import ClosableDialogTitle from "./ClosableDialogTitle";
import { addTestCase, getTestcaseSample, submitScenarioJob } from "../api/client";

const LIFECYCLE_ROLES = ["independent", "create", "read", "update", "delete"];

const BLANK_FORM = {
  test_scenario: "",
  lifecycle_role: "independent",
  path_params: {},
  query_params: {},
  headers: {},
  request_data: {},
  files: {},
  expected_response: { status_code: 200, required_fields: [], field_types: {} },
  steps: [],
};

export default function AddTestCaseDialog({ open, projectId, genId, results, onClose, onAdded, onScenarioQueued }) {
  const [tab, setTab] = useState("manual");
  const [target, setTarget] = useState("");
  const [loadingSample, setLoadingSample] = useState(false);
  const [fileFields, setFileFields] = useState([]);
  const [acceptsFile, setAcceptsFile] = useState(false);
  const [form, setForm] = useState(BLANK_FORM);
  const [scenarioText, setScenarioText] = useState("");
  const [scenarioFiles, setScenarioFiles] = useState({});
  const [saving, setSaving] = useState(false);
  const [queueing, setQueueing] = useState(false);
  const [queuedMsg, setQueuedMsg] = useState("");
  const [err, setErr] = useState("");

  const endpoints = (results || []).map((r) => ({ endpoint: r.endpoint, method: r.method }));
  const [method, endpoint] = target ? target.split("::") : ["", ""];
  const controlsDisabled = !target || loadingSample;

  const reset = () => {
    setTab("manual");
    setTarget("");
    setForm(BLANK_FORM);
    setFileFields([]);
    setAcceptsFile(false);
    setScenarioText("");
    setScenarioFiles({});
    setQueuedMsg("");
    setErr("");
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSelectTarget = async (value) => {
    setTarget(value);
    setQueuedMsg("");
    setErr("");
    if (!value) return;
    const [m, ep] = value.split("::");
    try {
      setLoadingSample(true);
      const { sample, file_fields, accepts_file } = await getTestcaseSample(projectId, genId, ep, m);
      setForm(sample);
      setFileFields(file_fields || []);
      setAcceptsFile(accepts_file);
      setScenarioFiles({});
    } catch (e) {
      setErr(e.response?.data?.error || "Failed to load endpoint schema");
    } finally {
      setLoadingSample(false);
    }
  };

  const handleSaveManual = async () => {
    try {
      setSaving(true);
      setErr("");
      const saved = await addTestCase(projectId, genId, { ...form, endpoint, method });
      onAdded(saved, endpoint, method);
      handleClose();
    } catch (e) {
      setErr(e.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleQueueScenario = async () => {
    try {
      setQueueing(true);
      setErr("");
      const job = await submitScenarioJob(projectId, genId, {
        endpoint,
        method,
        scenario: scenarioText,
        files: scenarioFiles,
      });
      setQueuedMsg(`Queued as job #${job.id} - it'll show up in "Needs Review" once it finishes.`);
      setScenarioText("");
      setScenarioFiles({});
      onScenarioQueued?.();
    } catch (e) {
      setErr(e.response?.data?.error || "Failed to queue scenario");
    } finally {
      setQueueing(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <ClosableDialogTitle onClose={handleClose}>Add Test Case</ClosableDialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}

        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2, mt: 1 }}>
          <TextField
            select
            label="Endpoint"
            fullWidth
            value={target}
            onChange={(e) => handleSelectTarget(e.target.value)}
          >
            {endpoints.map(({ endpoint: ep, method: m }) => (
              <MenuItem key={`${m}::${ep}`} value={`${m}::${ep}`}>
                {m} {ep}
              </MenuItem>
            ))}
          </TextField>
          {loadingSample && <CircularProgress size={20} />}
        </Box>

        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
          <Tab label="Manual" value="manual" />
          <Tab label="From Scenario" value="scenario" />
        </Tabs>

        {tab === "manual" && (
          <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto", pr: 1.5 }}>
            <TextField
              label="Test Scenario" fullWidth sx={{ mb: 2 }} disabled={controlsDisabled}
              value={form.test_scenario || ""}
              onChange={(e) => setForm({ ...form, test_scenario: e.target.value })}
            />
            <TextField
              select label="Lifecycle Role" fullWidth sx={{ mb: 2 }} disabled={controlsDisabled}
              value={form.lifecycle_role || "independent"}
              onChange={(e) => setForm({ ...form, lifecycle_role: e.target.value })}
            >
              {LIFECYCLE_ROLES.map((role) => (
                <MenuItem key={role} value={role}>{role}</MenuItem>
              ))}
            </TextField>
            <JsonField label="Path Params" value={form.path_params || {}} disabled={controlsDisabled}
              onChange={(v) => setForm({ ...form, path_params: v })} />
            <JsonField label="Query Params" value={form.query_params || {}} disabled={controlsDisabled}
              onChange={(v) => setForm({ ...form, query_params: v })} />
            <JsonField label="Headers" value={form.headers || {}} disabled={controlsDisabled}
              onChange={(v) => setForm({ ...form, headers: v })} />
            <JsonField label="Request Data" value={form.request_data || {}} disabled={controlsDisabled}
              onChange={(v) => setForm({ ...form, request_data: v })} />
            <FileFieldEditor
              projectId={projectId} genId={genId}
              files={form.files || {}} fileFields={fileFields} acceptsFile={acceptsFile}
              disabled={controlsDisabled}
              onChange={(files) => setForm({ ...form, files })}
            />
            <JsonField label="Expected Response" value={form.expected_response || {}} disabled={controlsDisabled}
              onChange={(v) => setForm({ ...form, expected_response: v })} />
            <StepsField label="Steps" value={form.steps || []} disabled={controlsDisabled}
              onChange={(steps) => setForm({ ...form, steps })} />
          </Box>
        )}

        {tab === "scenario" && (
          <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto", pr: 1.5 }}>
            {queuedMsg && <Alert severity="success" sx={{ mb: 2 }}>{queuedMsg}</Alert>}
            <TextField
              label="Describe the scenario this test case should cover"
              placeholder='e.g. "Creating a student with a duplicate email should fail with 400"'
              fullWidth multiline minRows={13} sx={{ mb: 2 }} disabled={controlsDisabled}
              inputProps={{ style: { overflow: "hidden" } }}
              value={scenarioText}
              onChange={(e) => setScenarioText(e.target.value)}
            />
            <FileFieldEditor
              projectId={projectId} genId={genId}
              files={scenarioFiles} fileFields={fileFields} acceptsFile={acceptsFile}
              disabled={controlsDisabled}
              onChange={setScenarioFiles}
            />
            <Alert severity="info" sx={{ mt: 1 }}>
              This testcase generation request will be queued. Once it finishes, it'll show up in the "Needs Review" tab where you can approve, edit or delete it.
            </Alert>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={handleClose}>Close</Button>
        {tab === "manual" && (
          <Button variant="contained" onClick={handleSaveManual} disabled={controlsDisabled || saving}>
            {saving ? <CircularProgress size={20} /> : "Save"}
          </Button>
        )}
        {tab === "scenario" && (
          <Button
            variant="contained"
            onClick={handleQueueScenario}
            disabled={controlsDisabled || queueing || !scenarioText.trim()}
          >
            {queueing ? <CircularProgress size={20} /> : "Submit"}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
