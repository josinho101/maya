import { useEffect, useMemo, useState } from "react";
import { Box, Card, CardContent, MenuItem, Select, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getExecutionResults } from "../api/client";

const COLORS = {
  passed:   "#66BB6A",
  failed:   "#EF5350",
  skipped:  "#FFB74D",
  duration: "#7C4DFF",
  endpoint: "#29B6F6",
  active:   "#FDD835",
  grid:     "#2A2A4A",
  tick:     "#aaa",
  cardBg:   "#1A1A2E",
};

const TOOLTIP_STYLE = {
  backgroundColor: "#1A1A2E",
  border: `1px solid ${COLORS.grid}`,
  borderRadius: 8,
};

const AXIS_PROPS = {
  tick: { fill: COLORS.tick, fontSize: 12 },
  axisLine: { stroke: COLORS.grid },
  tickLine: false,
};

const MAX_ENDPOINT_EXECUTIONS = 20;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const NUMERIC_RE = /^-?\d+$/;

// `path_params` is unreliable (often empty even when the URL has a real id,
// e.g. verify-after-create/update/delete steps), so dynamic segments are also
// detected heuristically and always collapsed to a generic `{id}` placeholder
// for consistent grouping regardless of which detection path caught them.
function isDynamicSegment(seg, pathParams) {
  if (seg === "None" || NUMERIC_RE.test(seg) || UUID_RE.test(seg)) return true;
  return Object.values(pathParams || {}).some(
    (v) => v !== null && v !== undefined && String(seg) === String(v)
  );
}

function normalizeEndpoint(method, urlStr, pathParams) {
  if (!method || !urlStr) return null;
  let pathname;
  try {
    pathname = new URL(urlStr).pathname;
  } catch {
    return null;
  }
  pathname = pathname.replace(/\/+/g, "/") || "/";
  // index 0 is always "" (the path starts with "/") - never treat it as
  // dynamic, even if path_params happens to carry an empty-string value.
  const segments = pathname
    .split("/")
    .map((seg, i) => (i > 0 && isDynamicSegment(seg, pathParams) ? "{id}" : seg));
  return `${method} ${segments.join("/")}`;
}

function useEndpointPerformance(projectId, executions) {
  const recent = useMemo(
    () =>
      executions
        .filter((e) => e.status === "COMPLETED" && e.started_at)
        .slice(0, MAX_ENDPOINT_EXECUTIONS)
        .reverse(),
    [executions]
  );
  const recentKey = recent.map((e) => e.id).join(",");

  const [seriesByEndpoint, setSeriesByEndpoint] = useState({});
  const [endpoints, setEndpoints] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!projectId || recent.length === 0) {
      setSeriesByEndpoint({});
      setEndpoints([]);
      return;
    }
    let cancelled = false;
    setLoading(true);

    Promise.all(
      recent.map((e) =>
        getExecutionResults(projectId, e.id)
          .then((results) => ({ exec: e, results }))
          .catch(() => null)
      )
    ).then((all) => {
      if (cancelled) return;

      const byEndpoint = {};
      all.forEach((entry, idx) => {
        if (!entry) return;
        const { exec, results } = entry;
        const date = new Date(exec.started_at).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });

        const timesThisExec = {};
        results.forEach((r) => {
          if (r.status === "SKIPPED") return;
          const key = normalizeEndpoint(
            r.request?.method,
            r.request?.url,
            r.request?.path_params
          );
          if (!key) return;
          (timesThisExec[key] ??= []).push(r.execution_time_ms ?? 0);
        });

        Object.entries(timesThisExec).forEach(([key, times]) => {
          const avg = times.reduce((a, b) => a + b, 0) / times.length;
          (byEndpoint[key] ??= []).push({
            idx,
            date,
            ms: Math.round(avg * 100) / 100,
          });
        });
      });

      setSeriesByEndpoint(byEndpoint);
      setEndpoints(Object.keys(byEndpoint).sort());
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, recentKey]);

  return { seriesByEndpoint, endpoints, loading };
}

export default function ExecutionCharts({ executions, projectId, stats, generationId }) {
  const nav = useNavigate();
  const leftTiles = [
    { label: "Total Test Cases", value: stats.totalTestCases, color: COLORS.endpoint, tab: "all" },
    { label: "Needs Review", value: stats.pendingReviewCount, color: COLORS.skipped, tab: "needs_review" },
  ];
  const rightTiles = [
    { label: "Active Jobs", value: stats.activeJobCount, color: COLORS.active, tab: "active" },
    { label: "Environments", value: stats.environmentCount ?? "—", color: COLORS.passed, tab: "environments" },
  ];
  const goToTab = (tab) => nav(`/projects/${projectId}/generations/${generationId}?jobsTab=${tab}`);

  const lastCompleted = executions.find((e) => e.status === "COMPLETED" && e.summary != null);
  const pieData = lastCompleted
    ? [
        { name: "Passed", value: lastCompleted.summary.passed, color: COLORS.passed },
        { name: "Failed", value: lastCompleted.summary.failed, color: COLORS.failed },
        { name: "Skipped", value: lastCompleted.summary.skipped, color: COLORS.skipped },
      ].filter((d) => d.value > 0)
    : [];

  const rawData = executions
    .filter(
      (e) =>
        e.status === "COMPLETED" &&
        e.summary != null &&
        e.started_at &&
        e.completed_at
    )
    .slice(0, 10)
    .reverse()
    .map((e, i) => {
      const start = new Date(e.started_at);
      const end = new Date(e.completed_at);
      return {
        idx: i,
        date: start.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        passed: e.summary.passed,
        failed: e.summary.failed,
        durationMs: end - start,
      };
    });

  const maxMs = rawData.length ? Math.max(...rawData.map((d) => d.durationMs)) : 0;
  const useMs = maxMs < 1000;
  const unit = useMs ? "ms" : "s";

  const chartData = rawData.map((d) => ({
    ...d,
    duration: useMs
      ? Math.round(d.durationMs)
      : Math.round(d.durationMs / 100) / 10,
  }));

  const hasTrendData = chartData.length >= 2;
  const dateLabel = (i) => chartData[i]?.date ?? i;

  const { seriesByEndpoint, endpoints } = useEndpointPerformance(projectId, executions);
  const [selectedEndpoint, setSelectedEndpoint] = useState("");

  useEffect(() => {
    if (endpoints.length > 0 && !endpoints.includes(selectedEndpoint)) {
      setSelectedEndpoint(endpoints[0]);
    }
  }, [endpoints, selectedEndpoint]);

  const endpointData = seriesByEndpoint[selectedEndpoint] ?? [];
  const endpointDateLabel = (i) =>
    endpointData.find((d) => d.idx === i)?.date ?? i;

  return (
    <>
      <Box sx={{ display: "flex", gap: 2, mb: 2, width: "100%" }}>
        {/* Summary tiles */}
        <Box
          sx={{
            flex: 1,
            minWidth: 0,
            display: "grid",
            gridTemplateColumns: "1fr",
            gridTemplateRows: "1fr 1fr",
            gap: 1.5,
          }}
        >
          {leftTiles.map((t) => (
            <Card
              key={t.label}
              sx={{
                height: "100%",
                cursor: generationId ? "pointer" : "default",
                "&:hover": generationId ? { backgroundColor: "action.hover" } : undefined,
              }}
              onClick={generationId ? () => goToTab(t.tab) : undefined}
            >
              <CardContent
                sx={{
                  height: "100%",
                  textAlign: "center",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                }}
              >
                <Typography variant="h5" fontWeight={700} sx={{ fontSize: "3rem", color: t.color }}>{t.value ?? "—"}</Typography>
                <Typography variant="caption" color="text.secondary">{t.label}</Typography>
              </CardContent>
            </Card>
          ))}
        </Box>

        {/* Last-execution outcome pie chart */}
        <Box sx={{ flex: 2, minWidth: 0 }}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Last Execution Outcome
              </Typography>
              {pieData.length > 0 ? (
                <Box sx={{ position: "relative" }}>
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="name"
                        cy="44%"
                        innerRadius="55%"
                        outerRadius="85%"
                        paddingAngle={3}
                        cornerRadius={6}
                      >
                        {pieData.map((d) => (
                          <Cell key={d.name} fill={d.color} stroke={COLORS.cardBg} strokeWidth={3} />
                        ))}
                      </Pie>
                      <Legend
                        wrapperStyle={{ fontSize: 12 }}
                        iconType="circle"
                        iconSize={8}
                        formatter={(value, entry) => `${value} (${entry.payload.value})`}
                      />
                    </PieChart>
                  </ResponsiveContainer>
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
                      {lastCompleted.summary.success_rate}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Pass Rate
                    </Typography>
                  </Box>
                </Box>
              ) : (
                <Typography color="text.secondary" variant="body2">
                  No completed execution yet. Data will be populated once an execution finishes.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Box>

        {/* Pass / Fail chart */}
        <Box sx={{ flex: 4, minWidth: 0 }}>
          {hasTrendData ? (
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Pass / Fail Over Time
                </Typography>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                    <XAxis dataKey="idx" tickFormatter={dateLabel} {...AXIS_PROPS} />
                    <YAxis allowDecimals={false} width={32} {...AXIS_PROPS} />
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      labelFormatter={dateLabel}
                    />
                    <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                    <Line
                      type="monotone"
                      dataKey="passed"
                      name="Passed"
                      stroke={COLORS.passed}
                      strokeWidth={2}
                      dot={{ r: 4, fill: COLORS.passed }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="failed"
                      name="Failed"
                      stroke={COLORS.failed}
                      strokeWidth={2}
                      dot={{ r: 4, fill: COLORS.failed }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          ) : (
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  Execution Trends
                </Typography>
                <Typography color="text.secondary" variant="body2">
                  Not enough data to display trends. Complete at least 2 executions.
                </Typography>
              </CardContent>
            </Card>
          )}
        </Box>

        {/* Summary tiles (right of Pass/Fail chart) */}
        <Box
          sx={{
            flex: 1,
            minWidth: 0,
            display: "grid",
            gridTemplateColumns: "1fr",
            gridTemplateRows: "1fr 1fr",
            gap: 1.5,
          }}
        >
          {rightTiles.map((t) => (
            <Card
              key={t.label}
              sx={{
                height: "100%",
                cursor: generationId ? "pointer" : "default",
                "&:hover": generationId ? { backgroundColor: "action.hover" } : undefined,
              }}
              onClick={generationId ? () => goToTab(t.tab) : undefined}
            >
              <CardContent
                sx={{
                  height: "100%",
                  textAlign: "center",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                }}
              >
                <Typography variant="h5" fontWeight={700} sx={{ fontSize: "3rem", color: t.color }}>{t.value ?? "—"}</Typography>
                <Typography variant="caption" color="text.secondary">{t.label}</Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>

      {(hasTrendData || endpoints.length > 0) && (
        <Box sx={{ display: "flex", gap: 2, mb: 2, width: "100%" }}>
          {/* Duration chart */}
          {hasTrendData && (
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Total Execution Duration ({unit})
                  </Typography>
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                      <XAxis dataKey="idx" tickFormatter={dateLabel} {...AXIS_PROPS} />
                      <YAxis width={useMs ? 62 : 50} unit={unit} {...AXIS_PROPS} />
                      <Tooltip
                        contentStyle={TOOLTIP_STYLE}
                        labelFormatter={dateLabel}
                        formatter={(v) => [`${v}${unit}`, "Duration"]}
                      />
                      <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                      <Line
                        type="monotone"
                        dataKey="duration"
                        name={`Duration (${unit})`}
                        stroke={COLORS.duration}
                        strokeWidth={2}
                        dot={{ r: 4, fill: COLORS.duration }}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Box>
          )}

          {/* API Performance by Endpoint */}
          {endpoints.length > 0 && (
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      mb: 1,
                      flexWrap: "wrap",
                      gap: 1,
                    }}
                  >
                    <Typography variant="subtitle1" fontWeight={600}>
                      API Performance by Endpoint
                    </Typography>
                    <Select
                      size="small"
                      value={selectedEndpoint}
                      onChange={(e) => setSelectedEndpoint(e.target.value)}
                      sx={{ minWidth: 220, fontSize: 13, "& .MuiSelect-select": { py: 0.5 } }}
                    >
                      {endpoints.map((ep) => (
                        <MenuItem key={ep} value={ep} sx={{ fontSize: 13 }}>
                          {ep}
                        </MenuItem>
                      ))}
                    </Select>
                  </Box>
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={endpointData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                      <XAxis
                        dataKey="idx"
                        type="number"
                        domain={["dataMin", "dataMax"]}
                        tickFormatter={endpointDateLabel}
                        {...AXIS_PROPS}
                      />
                      <YAxis width={50} unit="ms" {...AXIS_PROPS} />
                      <Tooltip
                        contentStyle={TOOLTIP_STYLE}
                        labelFormatter={endpointDateLabel}
                        formatter={(v) => [`${v}ms`, "Execution Time"]}
                      />
                      <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                      <Line
                        type="monotone"
                        dataKey="ms"
                        name="Execution Time (ms)"
                        stroke={COLORS.endpoint}
                        strokeWidth={2}
                        dot={{ r: 4, fill: COLORS.endpoint }}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Box>
          )}
        </Box>
      )}
    </>
  );
}
