import { useEffect, useMemo, useState } from "react";
import { Box, Card, CardContent, MenuItem, Select, Typography } from "@mui/material";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getExecutionResults } from "../api/client";

const COLORS = {
  passed:   "#66BB6A",
  failed:   "#EF5350",
  duration: "#7C4DFF",
  endpoint: "#29B6F6",
  grid:     "#2A2A4A",
  tick:     "#aaa",
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

export default function ExecutionCharts({ executions, projectId }) {
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
      {hasTrendData ? (
        <Box sx={{ display: "flex", gap: 2, mb: 2, width: "100%" }}>
          {/* Pass / Fail chart */}
          <Box sx={{ flex: 1, minWidth: 0 }}>
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
          </Box>

          {/* Duration chart */}
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
        </Box>
      ) : (
        <Card sx={{ mb: 2 }}>
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

      {endpoints.length > 0 && (
        <Card sx={{ mb: 2, width: "100%" }}>
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
            <ResponsiveContainer width="100%" height={300}>
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
      )}
    </>
  );
}
