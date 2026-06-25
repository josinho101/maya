import { Chip } from "@mui/material";

const STATUS_CONFIG = {
  PENDING:    { color: "default",  label: "Pending" },
  GENERATING: { color: "warning",  label: "Generating" },
  REVIEW:     { color: "info",     label: "Ready for Review" },
  APPROVED:   { color: "success",  label: "Approved" },
  FAILED:     { color: "error",    label: "Failed" },
  STOPPED:    { color: "default",  label: "Stopped" },
  QUEUED:     { color: "default",  label: "Queued" },
  CANCELLED:  { color: "default",  label: "Cancelled" },
  DONE:       { color: "success",  label: "Done" },
  RUNNING:    { color: "warning",  label: "Running" },
  COMPLETED:  { color: "success",  label: "Completed" },
};

export default function StatusChip({ status, size = "small" }) {
  const cfg = STATUS_CONFIG[status] || { color: "default", label: status };
  return <Chip label={cfg.label} color={cfg.color} size={size} />;
}
