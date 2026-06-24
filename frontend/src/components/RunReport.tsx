import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Box,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { apiClient, type RunSummary } from "../api/client";

export default function RunReport() {
  const { runId } = useParams<{ runId: string }>();
  const [summary, setSummary] = useState<RunSummary | null>(null);

  useEffect(() => {
    if (!runId) return;
    apiClient.getRun(runId).then(setSummary);
  }, [runId]);

  if (!summary) return null;

  return (
    <Box>
      <Typography variant="h6">{summary.run_id}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Environment: {summary.environment_id} · Total job time: {summary.total_job_time_ms} ms
      </Typography>

      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Test case</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Execution time (ms)</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {summary.results.map((result) => (
            <TableRow key={result.test_case_id}>
              <TableCell>{result.test_case_id}</TableCell>
              <TableCell>
                <Chip
                  size="small"
                  label={result.status}
                  color={result.status === "pass" ? "success" : "error"}
                />
              </TableCell>
              <TableCell>{result.execution_time_ms}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}
