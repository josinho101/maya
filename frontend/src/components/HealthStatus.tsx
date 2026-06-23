import { useEffect, useState } from "react";
import { Chip } from "@mui/material";
import { apiClient } from "../api/client";

type Status = "checking" | "ok" | "error";

export default function HealthStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    apiClient
      .getHealth()
      .then((response) => setStatus(response.status === "ok" ? "ok" : "error"))
      .catch(() => setStatus("error"));
  }, []);

  const label =
    status === "checking" ? "Connecting..." : status === "ok" ? "Server Connected" : "API: Server Unreachable";
  const color = status === "ok" ? "success" : status === "error" ? "error" : "default";

  return <Chip size="small" label={label} color={color} />;
}
