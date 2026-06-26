import { Box, Card, CardContent, Typography } from "@mui/material";
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

const COLORS = {
  passed:   "#66BB6A",
  failed:   "#EF5350",
  duration: "#7C4DFF",
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

export default function ExecutionCharts({ executions }) {
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

  if (chartData.length < 2) {
    return (
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
    );
  }

  const dateLabel = (i) => chartData[i]?.date ?? i;

  return (
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
  );
}
