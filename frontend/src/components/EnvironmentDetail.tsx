import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import DeleteIcon from "@mui/icons-material/Delete";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import {
  Box,
  Button,
  Divider,
  IconButton,
  MenuItem,
  Select,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { apiClient, type Environment, type UIPackage } from "../api/client";
import ConfirmDeleteDialog from "./ConfirmDeleteDialog";

interface EnvironmentDetailProps {
  projectId: string;
}

const AUTH_STRATEGIES = ["none", "basic", "form_login", "sso_manual"];

function emptyUiPackage(): UIPackage {
  return { base_url: "", auth: null, env_vars: {}, upload_fixtures: [], instructions: null };
}

export default function EnvironmentDetail({ projectId }: EnvironmentDetailProps) {
  const { envId } = useParams<{ envId: string }>();
  const navigate = useNavigate();
  const [environment, setEnvironment] = useState<Environment | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const [baseUrl, setBaseUrl] = useState("");
  const [authStrategy, setAuthStrategy] = useState("none");
  const [secureRef, setSecureRef] = useState("");
  const [envVars, setEnvVars] = useState<[string, string][]>([]);
  const [instructions, setInstructions] = useState("");

  useEffect(() => {
    if (!projectId || !envId) return;
    apiClient.getEnvironment(projectId, envId).then((env) => {
      setEnvironment(env);
      const ui = (env.packages.ui as UIPackage | undefined) ?? emptyUiPackage();
      setBaseUrl(ui.base_url ?? "");
      setAuthStrategy(ui.auth?.strategy ?? "none");
      setSecureRef(ui.auth?.secure_ref ?? "");
      setEnvVars(Object.entries(ui.env_vars ?? {}));
      setInstructions(ui.instructions ?? "");
    });
  }, [projectId, envId]);

  if (!environment || !envId) return null;

  const handleSavePackage = async () => {
    const env_vars = Object.fromEntries(envVars.filter(([key]) => key.trim().length > 0));
    const updated = await apiClient.updatePackage(projectId, envId, "ui", {
      base_url: baseUrl,
      auth: authStrategy === "none" ? null : { strategy: authStrategy, secure_ref: secureRef },
      env_vars,
      instructions: instructions || null,
    });
    setEnvironment(updated);
  };

  const handleDelete = async () => {
    await apiClient.deleteEnvironment(projectId, envId);
    setDeleteOpen(false);
    navigate("..");
  };

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Typography variant="h6">{environment.label}</Typography>
        <IconButton aria-label="delete environment" onClick={() => setDeleteOpen(true)}>
          <DeleteIcon />
        </IconButton>
      </Box>
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
      >
        Schedule: {environment.schedule?.cron ?? "none"} · Destructive-safe:{" "}
        {environment.is_destructive_safe ? "yes" : "no"}
        <Tooltip title="Destructive-safe means it's okay for automated tests to delete or modify data in this environment.">
          <InfoOutlinedIcon fontSize="inherit" sx={{ cursor: "help" }} />
        </Tooltip>
      </Typography>

      <Divider sx={{ my: 2 }} />

      <Typography variant="subtitle1">UI Package</Typography>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2, maxWidth: 480, mt: 1 }}>
        <TextField
          label="Base URL"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          fullWidth
        />
        <Select value={authStrategy} onChange={(e) => setAuthStrategy(e.target.value)}>
          {AUTH_STRATEGIES.map((strategy) => (
            <MenuItem key={strategy} value={strategy}>
              {strategy}
            </MenuItem>
          ))}
        </Select>
        {authStrategy !== "none" && (
          <TextField
            label="Secret reference (e.g. ${secure.<project>.<env>.<key>})"
            value={secureRef}
            onChange={(e) => setSecureRef(e.target.value)}
            fullWidth
          />
        )}
        <Box>
          <Typography variant="body2">Env vars</Typography>
          {envVars.map(([key, value], index) => (
            <Box key={index} sx={{ display: "flex", gap: 1, mt: 1 }}>
              <TextField
                label="Key"
                value={key}
                onChange={(e) =>
                  setEnvVars((current) =>
                    current.map((pair, i) => (i === index ? [e.target.value, pair[1]] : pair)),
                  )
                }
              />
              <TextField
                label="Value"
                value={value}
                onChange={(e) =>
                  setEnvVars((current) =>
                    current.map((pair, i) => (i === index ? [pair[0], e.target.value] : pair)),
                  )
                }
              />
              <Button
                onClick={() => setEnvVars((current) => current.filter((_, i) => i !== index))}
              >
                Remove
              </Button>
            </Box>
          ))}
          <Button sx={{ mt: 1 }} onClick={() => setEnvVars((current) => [...current, ["", ""]])}>
            Add env var
          </Button>
        </Box>
        <TextField
          label="Instructions"
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          multiline
          minRows={3}
          fullWidth
        />
        <Button variant="contained" onClick={handleSavePackage} sx={{ alignSelf: "flex-start" }}>
          Save UI Package
        </Button>
      </Box>

      <Divider sx={{ my: 2 }} />

      <Box sx={{ opacity: 0.5, pointerEvents: "none" }}>
        <Typography variant="subtitle1">API Package</Typography>
        <Typography variant="body2">API package configuration coming soon (F17).</Typography>
      </Box>

      <ConfirmDeleteDialog
        open={deleteOpen}
        title="Delete environment"
        message={`Delete "${environment.label}"? It will be archived, not removed from disk.`}
        onConfirm={handleDelete}
        onClose={() => setDeleteOpen(false)}
      />
    </Box>
  );
}
