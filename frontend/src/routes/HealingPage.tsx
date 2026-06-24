import { useEffect, useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { Box } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { apiClient, type Project, type TestCase } from "../api/client";
import HealingDetail from "../components/HealingDetail";

interface HealingPageProps {
  project: Project;
}

const COLUMNS: GridColDef<TestCase>[] = [
  { field: "id", headerName: "ID", flex: 1 },
  {
    field: "view_identity",
    headerName: "View",
    flex: 1,
    valueGetter: (_value, row) => (row.protocol === "ui" ? row.view_identity : ""),
  },
  {
    field: "locator_confidence",
    headerName: "Locator confidence",
    flex: 1,
    valueGetter: (_value, row) => (row.protocol === "ui" ? row.locator_confidence : ""),
  },
  { field: "last_run_status", headerName: "Last run", flex: 1 },
];

function HealingQueueList({ project }: HealingPageProps) {
  const navigate = useNavigate();
  const [testCases, setTestCases] = useState<TestCase[]>([]);

  useEffect(() => {
    apiClient.listTestCases(project.id, "needs_review", "ui").then(setTestCases);
  }, [project.id]);

  return (
    <Box>
      <DataGrid
        autoHeight
        rows={testCases}
        columns={COLUMNS}
        getRowId={(row) => row.id}
        onRowClick={(params) => navigate(params.id as string)}
        disableRowSelectionOnClick
      />
    </Box>
  );
}

export default function HealingPage({ project }: HealingPageProps) {
  return (
    <Routes>
      <Route index element={<HealingQueueList project={project} />} />
      <Route path=":testCaseId" element={<HealingDetail projectId={project.id} />} />
    </Routes>
  );
}
