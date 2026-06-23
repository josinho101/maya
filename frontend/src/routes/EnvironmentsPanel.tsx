import { useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import AddIcon from "@mui/icons-material/Add";
import {
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormHelperText,
  InputLabel,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import { ApiError, apiClient, type Project } from "../api/client";
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

function EnvironmentList({ project }: EnvironmentsPanelProps) {
  const navigate = useNavigate();
  const [environments, setEnvironments] = useState(project.environments);
  const [open, setOpen] = useState(false);
  const [tag, setTag] = useState("");
  const [preset, setPreset] = useState<string>(DEFAULT_PRESET);
  const [customCron, setCustomCron] = useState("");
  const [isDestructiveSafe, setIsDestructiveSafe] = useState(false);
  const [tagError, setTagError] = useState<string | null>(null);

  const effectiveCron = preset === "custom" ? customCron : preset;

  const closeDialog = () => {
    setOpen(false);
    setTag("");
    setPreset(DEFAULT_PRESET);
    setCustomCron("");
    setIsDestructiveSafe(false);
    setTagError(null);
  };

  const handleAdd = async () => {
    try {
      const created = await apiClient.addEnvironment(project.id, {
        tag,
        schedule: { cron: effectiveCron },
        is_destructive_safe: isDestructiveSafe,
      });
      setEnvironments((current) => [...current, created.id]);
      closeDialog();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setTagError(err.detail ?? "An environment with this tag already exists.");
      } else {
        throw err;
      }
    }
  };

  return (
    <Box>
      <List>
        {environments.map((envId) => (
          <ListItemButton key={envId} onClick={() => navigate(envId)}>
            <ListItemText primary={envId} />
          </ListItemButton>
        ))}
      </List>
      <Button startIcon={<AddIcon />} onClick={() => setOpen(true)}>
        Add Environment
      </Button>

      <Dialog open={open} onClose={closeDialog} fullWidth maxWidth="sm">
        <DialogTitle>Add Environment</DialogTitle>
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
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog}>Cancel</Button>
          <Button variant="contained" disabled={!tag.trim()} onClick={handleAdd}>
            Add
          </Button>
        </DialogActions>
      </Dialog>
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
