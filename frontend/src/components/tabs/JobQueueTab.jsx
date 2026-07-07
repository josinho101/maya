import { Box, Typography, Table, TableBody, TableCell, TableHead, TableRow, IconButton, Tooltip } from "@mui/material";
import StopIcon from "@mui/icons-material/Stop";
import StatusChip from "../StatusChip";

export default function JobQueueTab({ jobs, isActive, isAdmin, onStopJob }) {
  if (jobs.length === 0) {
    return (
      <Typography color="text.secondary" variant="body2">
        {isActive ? "Nothing queued or running." : "No completed jobs yet."}
      </Typography>
    );
  }

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Endpoint</TableCell>
          <TableCell>Scenario</TableCell>
          <TableCell>Status</TableCell>
          <TableCell>Result</TableCell>
          {isActive && <TableCell align="right">Actions</TableCell>}
        </TableRow>
      </TableHead>
      <TableBody>
        {jobs.map((job) => (
          <TableRow key={job.id} hover>
            <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>
              {job.method} {job.endpoint}
            </TableCell>
            <TableCell sx={{ maxWidth: 320, overflowWrap: "break-word" }}>{job.scenario}</TableCell>
            <TableCell><StatusChip status={job.status} /></TableCell>
            <TableCell>
              {job.status === "DONE" && (
                <Typography variant="caption" sx={{ fontFamily: "monospace" }}>{job.tc_id}</Typography>
              )}
              {job.status === "FAILED" && (
                <Typography variant="caption" color="error">{job.error}</Typography>
              )}
            </TableCell>
            {isActive && (
              <TableCell align="right">
                {isAdmin && (
                  <Tooltip title="Stop this job">
                    <IconButton size="small" color="error" onClick={() => onStopJob(job.id)}>
                      <StopIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
