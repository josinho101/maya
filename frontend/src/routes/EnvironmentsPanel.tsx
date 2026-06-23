import { useEffect, useRef, useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import AddIcon from "@mui/icons-material/Add";
import ArchiveIcon from "@mui/icons-material/Archive";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormHelperText,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { ApiError, apiClient, type Environment, type Project } from "../api/client";
import ConfirmDeleteDialog from "../components/ConfirmDeleteDialog";
import EnvironmentDetail from "../components/EnvironmentDetail";

interface EnvironmentsPanelProps {
  project: Project;
}

const CRON_PRESETS = [
  { value: "0 * * * *", label: "Every hour" },
  { value: "0 */6 * * *", label: "Every 6 hours" },
  { value: "0 0 * * *", label: "Daily at midnight" },
  { value: "custom", label: "Custom..." },
] as const;

const DEFAULT_PRESET = "0 */6 * * *";

function presetForCron(cron: string | null | undefined): string {
  if (!cron) return DEFAULT_PRESET;
  const known = CRON_PRESETS.find((p) => p.value === cron);
  return known ? known.value : "custom";
}

function EnvironmentList({ project }: EnvironmentsPanelProps) {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [archiveTarget, setArchiveTarget] = useState<Environment | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Environment | null>(null);

  const [open, setOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"create" | "edit">("create");
  const [editTarget, setEditTarget] = useState<Environment | null>(null);
  const [activeTab, setActiveTab] = useState<"manual" | "upload">("manual");
  const [tag, setTag] = useState("");
  const [preset, setPreset] = useState<string>(DEFAULT_PRESET);
  const [customCron, setCustomCron] = useState("");
  const [isDestructiveSafe, setIsDestructiveSafe] = useState(false);
  const [tagError, setTagError] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  const [baseUrl, setBaseUrl] = useState("");
  const [authStrategy, setAuthStrategy] = useState("none");
  const [secureRef, setSecureRef] = useState("");
  const [envVars, setEnvVars] = useState<[string, string][]>([]);
  const [hasPackageFields, setHasPackageFields] = useState(false);

  const effectiveCron = preset === "custom" ? customCron : preset;

  const refresh = () => {
    apiClient.listEnvironments(project.id).then(setEnvironments);
  };

  useEffect(refresh, [project.id]);

  const closeDialog = () => {
    setOpen(false);
    setDialogMode("create");
    setEditTarget(null);
    setActiveTab("manual");
    setTag("");
    setPreset(DEFAULT_PRESET);
    setCustomCron("");
    setIsDestructiveSafe(false);
    setTagError(null);
    setImportError(null);
    setBaseUrl("");
    setAuthStrategy("none");
    setSecureRef("");
    setEnvVars([]);
    setHasPackageFields(false);
  };

  const openCreateDialog = () => {
    setDialogMode("create");
    setOpen(true);
  };

  const openEditDialog = (env: Environment) => {
    setDialogMode("edit");
    setEditTarget(env);
    setTag(env.label);
    setPreset(presetForCron(env.schedule?.cron));
    setCustomCron(presetForCron(env.schedule?.cron) === "custom" ? env.schedule?.cron ?? "" : "");
    setIsDestructiveSafe(env.is_destructive_safe);
    setActiveTab("manual");
    setOpen(true);
  };

  const handleDownloadSampleJson = async () => {
    const blob = await apiClient.downloadEnvironmentSampleJson();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "environment-sample.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleUploadJson = async (file: File) => {
    setImportError(null);
    try {
      const manifest = await apiClient.parseEnvironmentJson(file);
      setTag(manifest.tag);
      setPreset(presetForCron(manifest.schedule?.cron));
      setCustomCron(presetForCron(manifest.schedule?.cron) === "custom" ? manifest.schedule?.cron ?? "" : "");
      setIsDestructiveSafe(manifest.is_destructive_safe);
      setBaseUrl(manifest.base_url);
      setAuthStrategy(manifest.auth?.strategy ?? "none");
      setSecureRef(manifest.auth?.secure_ref ?? "");
      setEnvVars(Object.entries(manifest.env_vars ?? {}));
      setHasPackageFields(true);
      setActiveTab("manual");
    } catch (err) {
      if (err instanceof ApiError) {
        setImportError(err.detail ?? "Could not read that file.");
      } else {
        throw err;
      }
    }
  };

  const handleSubmit = async () => {
    try {
      if (dialogMode === "edit" && editTarget) {
        await apiClient.updateEnvironment(project.id, editTarget.id, {
          label: tag,
          schedule: { cron: effectiveCron },
          is_destructive_safe: isDestructiveSafe,
        });
      } else {
        const created = await apiClient.addEnvironment(project.id, {
          tag,
          schedule: { cron: effectiveCron },
          is_destructive_safe: isDestructiveSafe,
        });
        if (hasPackageFields) {
          await apiClient.updatePackage(project.id, created.id, "ui", {
            base_url: baseUrl,
            auth: authStrategy === "none" ? null : { strategy: authStrategy, secure_ref: secureRef },
            env_vars: Object.fromEntries(envVars.filter(([key]) => key.trim().length > 0)),
          });
        }
      }
      refresh();
      closeDialog();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setTagError(err.detail ?? "An environment with this tag already exists.");
      } else {
        throw err;
      }
    }
  };

  const handleArchive = async () => {
    if (!archiveTarget) return;
    await apiClient.archiveEnvironment(project.id, archiveTarget.id);
    setEnvironments((current) => current.filter((e) => e.id !== archiveTarget.id));
    setArchiveTarget(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await apiClient.deleteEnvironment(project.id, deleteTarget.id);
    setEnvironments((current) => current.filter((e) => e.id !== deleteTarget.id));
    setDeleteTarget(null);
  };

  return (
    <Box>
      <Button startIcon={<AddIcon />} onClick={openCreateDialog} sx={{ mb: 2 }}>
        Add Environment
      </Button>

      <Grid container spacing={2}>
        {environments.map((env) => (
          <Grid key={env.id} size={{ xs: 12, sm: 6, md: 3, lg: 2 }}>
            <Card sx={{ width: "100%", minWidth: 0 }}>
              <CardContent sx={{ cursor: "pointer", minWidth: 0 }} onClick={() => navigate(env.id)}>
                <Tooltip title={env.label}>
                  <Typography variant="h6" noWrap>
                    {env.label}
                  </Typography>
                </Tooltip>
                <Typography variant="body2" color="text.secondary" noWrap>
                  Schedule: {env.schedule?.cron ?? "none"}
                </Typography>
                <Typography variant="body2" color="text.secondary" noWrap>
                  Destructive-safe: {env.is_destructive_safe ? "yes" : "no"}
                </Typography>
              </CardContent>
              <CardActions sx={{ justifyContent: "space-between" }}>
                <Button
                  aria-label={`open ${env.label}`}
                  variant="contained"
                  size="small"
                  endIcon={<ArrowForwardIcon />}
                  sx={{ borderRadius: 999 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(env.id);
                  }}
                >
                  OPEN
                </Button>
                <Box>
                  <IconButton
                    aria-label={`edit ${env.label}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      openEditDialog(env);
                    }}
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    aria-label={`archive ${env.label}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setArchiveTarget(env);
                    }}
                  >
                    <ArchiveIcon />
                  </IconButton>
                  <IconButton
                    aria-label={`delete ${env.label}`}
                    color="error"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTarget(env);
                    }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Box>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog open={open} onClose={closeDialog} fullWidth maxWidth="sm">
        <DialogTitle>{dialogMode === "edit" ? "Edit Environment" : "Add Environment"}</DialogTitle>
        {dialogMode === "create" && (
          <Tabs value={activeTab} onChange={(_, value) => setActiveTab(value)} sx={{ px: 3 }}>
            <Tab label="Fill manually" value="manual" />
            <Tab label="Upload JSON" value="upload" />
          </Tabs>
        )}
        {activeTab === "manual" && (
          <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
            <TextField
              label="Tag"
              value={tag}
              onChange={(e) => {
                setTag(e.target.value);
                setTagError(null);
              }}
              error={tagError !== null}
              helperText={tagError ?? "A short name for this environment, e.g. Dev, Staging, Production."}
              fullWidth
            />
            <FormControl fullWidth>
              <InputLabel id="schedule-preset-label">Run schedule</InputLabel>
              <Select
                labelId="schedule-preset-label"
                value={preset}
                label="Run schedule"
                onChange={(e) => setPreset(e.target.value)}
              >
                {CRON_PRESETS.map((p) => (
                  <MenuItem key={p.value} value={p.value}>
                    {p.label}
                  </MenuItem>
                ))}
              </Select>
              <FormHelperText>
                How often tests run automatically in this environment. Choose "Custom..." to enter
                your own cron expression.
              </FormHelperText>
            </FormControl>
            {preset === "custom" && (
              <TextField
                label="Custom cron expression"
                value={customCron}
                onChange={(e) => setCustomCron(e.target.value)}
                placeholder="0 */6 * * *"
                helperText='Format: minute hour day month weekday — e.g. "0 */6 * * *" runs every 6 hours.'
                fullWidth
              />
            )}
            <FormControlLabel
              control={
                <Checkbox
                  checked={isDestructiveSafe}
                  onChange={(e) => setIsDestructiveSafe(e.target.checked)}
                />
              }
              label="Destructive-safe"
            />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 4, mt: -1 }}>
              Check this if it's okay for automated tests to delete or modify data in this
              environment (e.g. a staging or test environment). Leave unchecked for environments
              containing real or important data (e.g. production).
            </Typography>
            {hasPackageFields && (
              <Typography variant="body2" color="text.secondary">
                Base URL, auth, and env vars from the uploaded file will be applied when this
                environment is added.
              </Typography>
            )}
          </DialogContent>
        )}
        {dialogMode === "create" && activeTab === "upload" && (
          <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Download the sample JSON, fill in your values, then upload it to populate the form.
            </Typography>
            <Button variant="outlined" onClick={handleDownloadSampleJson} sx={{ alignSelf: "flex-start" }}>
              Download sample JSON
            </Button>
            <Button
              variant="contained"
              onClick={() => fileInputRef.current?.click()}
              sx={{ alignSelf: "flex-start" }}
            >
              Upload JSON
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleUploadJson(file);
                e.target.value = "";
              }}
            />
            {importError && <Typography color="error">{importError}</Typography>}
          </DialogContent>
        )}
        <DialogActions>
          <Button onClick={closeDialog}>Cancel</Button>
          <Button variant="contained" disabled={!tag.trim()} onClick={handleSubmit}>
            {dialogMode === "edit" ? "Save" : "Add"}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDeleteDialog
        open={archiveTarget !== null}
        title="Archive environment"
        message={`Archive "${archiveTarget?.label}"? It will be hidden from this list, but its files stay on disk.`}
        confirmLabel="Archive"
        confirmColor="warning"
        onConfirm={handleArchive}
        onClose={() => setArchiveTarget(null)}
      />

      <ConfirmDeleteDialog
        open={deleteTarget !== null}
        title="Delete environment"
        message={`Permanently delete "${deleteTarget?.label}" and all its data? This cannot be undone.`}
        onConfirm={handleDelete}
        onClose={() => setDeleteTarget(null)}
      />
    </Box>
  );
}

export default function EnvironmentsPanel({ project }: EnvironmentsPanelProps) {
  return (
    <Routes>
      <Route index element={<EnvironmentList project={project} />} />
      <Route path=":envId" element={<EnvironmentDetail projectId={project.id} />} />
    </Routes>
  );
}
