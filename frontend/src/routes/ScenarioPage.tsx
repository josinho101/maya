import { useEffect, useRef, useState } from "react";
import { Link as RouterLink, Route, Routes, useNavigate, useParams } from "react-router-dom";
import {
  Box,
  Button,
  Chip,
  FormControl,
  InputLabel,
  Link as MuiLink,
  MenuItem,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import { apiClient, type Environment, type Project, type ScenarioSession } from "../api/client";

interface ScenarioPageProps {
  project: Project;
}

const TERMINAL_STATUSES = new Set(["completed", "stuck"]);

function ScenarioSubmitForm({ project }: ScenarioPageProps) {
  const navigate = useNavigate();
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [environmentId, setEnvironmentId] = useState("");
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.listEnvironments(project.id).then((envs) => {
      setEnvironments(envs);
      setEnvironmentId((current) => current || envs[0]?.id || "");
    });
  }, [project.id]);

  const handleSubmit = async () => {
    if (!environmentId || !text.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const session = await apiClient.submitScenario(project.id, environmentId, text);
      navigate(session.id);
    } catch {
      setError("Scenario submission failed. Check that the environment has a base URL configured.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Submit a business scenario
      </Typography>
      <TextField
        label="Scenario"
        placeholder="e.g. A user logs in and clicks the counter button"
        fullWidth
        multiline
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        sx={{ mb: 2 }}
      />
      <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel id="scenario-environment-label">Environment</InputLabel>
          <Select
            labelId="scenario-environment-label"
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
          disabled={!environmentId || !text.trim() || submitting}
          onClick={handleSubmit}
        >
          {submitting ? "Submitting…" : "Submit"}
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

function statusColor(status: ScenarioSession["status"]): "default" | "success" | "error" | "warning" {
  if (status === "completed") return "success";
  if (status === "stuck") return "error";
  return "warning";
}

function ScenarioStatus({ projectId }: { projectId: string }) {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<ScenarioSession | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    setSession(null);

    const fetchSession = () => {
      apiClient.getScenarioSession(projectId, sessionId).then((fetched) => {
        setSession(fetched);
        if (TERMINAL_STATUSES.has(fetched.status) && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      });
    };

    fetchSession();
    intervalRef.current = setInterval(fetchSession, 1500);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [projectId, sessionId]);

  if (!session) return null;

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Scenario status
      </Typography>
      <Typography sx={{ mb: 1 }}>{session.text}</Typography>
      <Chip size="small" label={session.status} color={statusColor(session.status)} sx={{ mb: 2 }} />
      {session.status === "completed" && session.resulting_test_case_id && (
        <Typography>
          <MuiLink component={RouterLink} to={`/projects/${projectId}/test-cases/${session.resulting_test_case_id}`}>
            View resulting test case
          </MuiLink>
        </Typography>
      )}
      {session.status === "stuck" && (
        <Typography color="error">
          Stuck: {session.stuck_reason}
          {session.blocked_at ? ` (at view ${session.blocked_at})` : ""}
        </Typography>
      )}
    </Box>
  );
}

export default function ScenarioPage({ project }: ScenarioPageProps) {
  return (
    <Routes>
      <Route index element={<ScenarioSubmitForm project={project} />} />
      <Route path=":sessionId" element={<ScenarioStatus projectId={project.id} />} />
    </Routes>
  );
}
