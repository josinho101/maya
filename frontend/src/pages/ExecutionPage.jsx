import { useState, useEffect, useCallback, useRef } from "react";
import {
  Box, Typography, Button, Card, CardContent, CircularProgress, Alert,
  LinearProgress, Divider, List, ListItemButton, ListItemText,
  ListItemIcon, Tooltip, IconButton,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutlined";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlined";
import HistoryIcon from "@mui/icons-material/History";
import ScienceIcon from "@mui/icons-material/Science";
import { useNavigate, useParams } from "react-router-dom";
import { PieChart, Pie, Cell, Legend, BarChart, Bar, XAxis, YAxis, Tooltip as ChartTooltip, ResponsiveContainer } from "recharts";
import {
  getExecution, listExecutions, executeGeneration, getReportUrl, getExecutionResults,
} from "../api/client";
import StatusChip from "../components/StatusChip";

const POLLING_STATUSES = ["PENDING", "RUNNING"];

const PIE_COLORS = {
  passed:  "#66BB6A",
  failed:  "#EF5350",
  skipped: "#FFB74D",
};

const METHOD_COLORS = {
  GET:    "#61AFFE",
  POST:   "#49CC90",
  PUT:    "#FCA130",
  PATCH:  "#50E3C2",
  DELETE: "#F93E3E",
};

function SummaryCard({ label, value, color }) {
  return (
    <Card>
      <CardContent sx={{ textAlign: "center", display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Typography variant="h5" fontWeight={700} sx={{ fontSize: "3rem", color }}>{value ?? "—"}</Typography>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
      </CardContent>
    </Card>
  );
}

export default function ExecutionPage() {
  const { execId } = useParams();
  return <ExecutionPageInner key={execId} />;
}

function ExecutionPageInner() {
  const { projectId, execId } = useParams();
  const nav = useNavigate();
  const pollRef = useRef(null);

  const [exec, setExec] = useState(null);
  const [history, setHistory] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rerunning, setRerunning] = useState(false);

  const fetchExec = useCallback(async () => {
    try {
      const data = await getExecution(projectId, execId);
      setExec(data);
      return data;
    } catch {
      setError("Failed to load execution");
    } finally {
      setLoading(false);
    }
  }, [projectId, execId]);

  const fetchHistory = useCallback(async () => {
    try {
      setHistory(await listExecutions(projectId));
    } catch { /* ignore */ }
  }, [projectId]);

  useEffect(() => {
    fetchExec().then((data) => {
      if (!data) return;
      if (data.status === "COMPLETED") {
        getExecutionResults(projectId, execId).then(setResults).catch(() => {});
      } else if (POLLING_STATUSES.includes(data.status)) {
        pollRef.current = setInterval(async () => {
          const d = await getExecution(projectId, execId).catch(() => null);
          if (d) {
            setExec(d);
            if (!POLLING_STATUSES.includes(d.status)) {
              clearInterval(pollRef.current);
              fetchHistory();
              if (d.status === "COMPLETED") {
                getExecutionResults(projectId, execId).then(setResults).catch(() => {});
              }
            }
          }
        }, 5000);
      }
    });
    fetchHistory();
    return () => clearInterval(pollRef.current);
  }, [projectId, execId, fetchExec, fetchHistory]);

  const handleRerun = async () => {
    try {
      setRerunning(true);
      const res = await executeGeneration(projectId, exec.generation_id, { environment_id: exec.environment_id });
      nav(`/projects/${projectId}/executions/${res.execution_id}`);
    } catch (e) {
      setError(e.response?.data?.error || "Re-run failed");
      setRerunning(false);
    }
  };

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}><CircularProgress /></Box>;

  const summary = exec?.summary;
  const canRerun = exec?.status === "COMPLETED" || exec?.status === "FAILED";

  const execDuration = (() => {
    if (!exec?.started_at || !exec?.completed_at) return "—";
    const ms = new Date(exec.completed_at) - new Date(exec.started_at);
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
  })();

  const pieData = summary
    ? [
        { name: "Passed",  value: summary.passed,  color: PIE_COLORS.passed  },
        { name: "Failed",  value: summary.failed,  color: PIE_COLORS.failed  },
        { name: "Skipped", value: summary.skipped, color: PIE_COLORS.skipped },
      ].filter((d) => d.value > 0)
    : [];

  const methodData = results.length
    ? Object.entries(
        results.reduce((acc, r) => {
          const m = r.request?.method;
          if (m) acc[m] = (acc[m] || 0) + 1;
          return acc;
        }, {})
      ).map(([method, count]) => ({ method, count }))
    : [];

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ display: "flex", gap: 2, mb: 3, alignItems: "center", flexWrap: "wrap" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flex: 1 }}>
          <IconButton size="small" onClick={() => nav(`/projects/${projectId}`)}>
            <ArrowBackIcon fontSize="small" />
          </IconButton>
          <Typography variant="h5" fontWeight={700}>Execution</Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center" }}>
          {exec?.status === "COMPLETED" && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<ScienceIcon />}
              onClick={() => nav(`/projects/${projectId}/generations/${exec.generation_id}`)}
            >
              View Test Cases
            </Button>
          )}
          {canRerun && (
            <Button
              variant="outlined"
              size="small"
              startIcon={rerunning ? <CircularProgress size={14} /> : <PlayArrowIcon />}
              onClick={handleRerun}
              disabled={rerunning}
            >
              Re-run Tests
            </Button>
          )}
          {exec?.status === "COMPLETED" && (
            <Button
              variant="contained"
              size="small"
              startIcon={<OpenInNewIcon />}
              onClick={() => window.open(getReportUrl(projectId, execId), "_blank")}
            >
              View Full Report
            </Button>
          )}
        </Box>
      </Box>

      <Box sx={{ display: "flex", gap: 3, alignItems: "flex-start", flexDirection: { xs: "column", md: "row" } }}>
        {/* Left: results */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {exec && POLLING_STATUSES.includes(exec.status) && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography fontWeight={600} gutterBottom>
                  {exec.status === "PENDING" ? "Queued..." : "Running test cases..."}
                </Typography>
                <LinearProgress sx={{ mt: 1 }} />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  Polling every 5 seconds.
                </Typography>
              </CardContent>
            </Card>
          )}

          {exec?.status === "FAILED" && (
            <Alert severity="error" sx={{ mb: 3 }}>
              Execution failed: {exec.error || "Unknown error"}
            </Alert>
          )}

          {exec?.status === "COMPLETED" && summary && pieData.length > 0 && (
            <Box sx={{ display: "flex", gap: 2, alignItems: "stretch" }}>
              {/* Left: 2 tiles + method bar chart */}
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, flex: 1 }}>
                <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1.5 }}>
                  <SummaryCard label="Total Testcases" value={summary.total} color="text.primary" />
                  <SummaryCard label="Total Execution Time" value={execDuration} color="text.primary" />
                </Box>
                <Card sx={{ flex: 1 }}>
                  <CardContent>
                    <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                      Requests by Method
                    </Typography>
                    {methodData.length > 0 ? (
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={methodData} barCategoryGap="30%">
                          <XAxis dataKey="method" tick={{ fontSize: 11 }} />
                          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                          <ChartTooltip cursor={{ fill: "transparent" }} contentStyle={{ background: "#fff", border: "none", borderRadius: 6, color: "#000" }} itemStyle={{ color: "#000" }} />
                          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                            {methodData.map((d) => (
                              <Cell key={d.method} fill={METHOD_COLORS[d.method] ?? "#90CAF9"} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
                        <CircularProgress size={24} />
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Box>

              {/* Right: pie chart */}
              <Card sx={{ flex: 1 }}>
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Execution Outcome
                  </Typography>
                  <Box sx={{ position: "relative", display: "flex", justifyContent: "center", mt: 5 }}>
                    <PieChart width={360} height={300}>
                      <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="48%"
                        innerRadius={85}
                        outerRadius={130}
                        paddingAngle={3}
                        cornerRadius={6}
                      >
                        {pieData.map((d) => (
                          <Cell key={d.name} fill={d.color} stroke="#1A1A2E" strokeWidth={3} />
                        ))}
                      </Pie>
                      <Legend
                        wrapperStyle={{ fontSize: 12 }}
                        iconType="circle"
                        iconSize={8}
                        formatter={(value, entry) => `${value} (${entry.payload.value})`}
                      />
                    </PieChart>
                    <Box
                      sx={{
                        position: "absolute",
                        top: "44%",
                        left: "50%",
                        transform: "translate(-50%, -50%)",
                        textAlign: "center",
                        pointerEvents: "none",
                      }}
                    >
                      <Typography variant="h5" fontWeight={700}>
                        {summary.success_rate}%
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Pass Rate
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Box>
          )}
        </Box>

        {/* Right: execution history */}
        <Box sx={{ width: { xs: "100%", md: 320 }, flexShrink: 0 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                <HistoryIcon fontSize="small" color="primary" />
                <Typography fontWeight={600}>Last 5 Execution History</Typography>
              </Box>
              <Divider sx={{ mb: 1 }} />
              {history.length === 0 ? (
                <Typography variant="body2" color="text.secondary">No history</Typography>
              ) : (
                <List dense disablePadding>
                  {history.slice(0, 5).map((h) => {
                    const isCurrent = h.id === execId;
                    return (
                      <ListItemButton
                        key={h.id}
                        selected={isCurrent}
                        onClick={() => !isCurrent && nav(`/projects/${projectId}/executions/${h.id}`)}
                        sx={{ borderRadius: 1, mb: 0.5 }}
                      >
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          {h.status === "COMPLETED" ? (
                            <CheckCircleOutlineIcon
                              fontSize="small"
                              color={h.summary?.failed > 0 ? "warning" : "success"}
                            />
                          ) : h.status === "FAILED" ? (
                            <ErrorOutlineIcon fontSize="small" color="error" />
                          ) : (
                            <CircularProgress size={16} />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                              <StatusChip status={h.status} />
                            </Box>
                          }
                          secondary={
                            <>
                              {new Date(h.started_at).toLocaleString()}
                              {h.environment_name && ` · ${h.environment_name}`}
                            </>
                          }
                        />
                        {h.status === "COMPLETED" && (
                          <Tooltip title="Open report">
                            <span>
                              <Button
                                size="small"
                                sx={{ minWidth: 0, p: 0.5 }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  window.open(getReportUrl(projectId, h.id), "_blank");
                                }}
                              >
                                <OpenInNewIcon fontSize="small" />
                              </Button>
                            </span>
                          </Tooltip>
                        )}
                      </ListItemButton>
                    );
                  })}
                </List>
              )}
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Box>
  );
}
