import { useEffect, useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from "@mui/material";
import { apiClient, type Environment, type Project } from "../api/client";
import RunReport from "../components/RunReport";

interface RunsPageProps {
  project: Project;
}

function RunTrigger({ project }: RunsPageProps) {
  const navigate = useNavigate();
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [environmentId, setEnvironmentId] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.listEnvironments(project.id).then((envs) => {
      setEnvironments(envs);
      setEnvironmentId((current) => current || envs[0]?.id || "");
    });
  }, [project.id]);

  const handleRunNow = async () => {
    if (!environmentId) return;
    setRunning(true);
    setError(null);
    try {
      const summary = await apiClient.triggerRun(project.id, environmentId);
      navigate(summary.run_id);
    } catch {
      setError("Run failed to start. Check that the environment has a base URL configured.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Run approved test cases
      </Typography>
      <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel id="run-environment-label">Environment</InputLabel>
          <Select
            labelId="run-environment-label"
            label="Environment"
            value={environmentId}
            onChange={(e) => setEnvironmentId(e.target.value)}
          >
            {environments.map((env) => (
              <MenuItem key={env.id} value={env.id}>
                {env.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button
          variant="contained"
          disabled={!environmentId || running}
          onClick={handleRunNow}
        >
          {running ? "Running…" : "Run Now"}
        </Button>
      </Box>
      {error && (
        <Typography color="error" sx={{ mt: 2 }}>
          {error}
        </Typography>
      )}
    </Box>
  );
}

export default function RunsPage({ project }: RunsPageProps) {
  return (
    <Routes>
      <Route index element={<RunTrigger project={project} />} />
      <Route path=":runId" element={<RunReport />} />
    </Routes>
  );
}
