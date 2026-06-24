import { useEffect, useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { Box, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { apiClient, type Project, type TestCase } from "../api/client";
import TestCaseDetail from "../components/TestCaseDetail";

interface TestCasesPageProps {
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
  { field: "created_by", headerName: "Created by", flex: 1 },
  {
    field: "tags",
    headerName: "Tags",
    flex: 1,
    valueGetter: (_value, row) => row.tags.join(", "),
  },
  {
    field: "locator_confidence",
    headerName: "Locator confidence",
    flex: 1,
    valueGetter: (_value, row) => (row.protocol === "ui" ? row.locator_confidence : ""),
  },
];

function TestCaseList({ project }: TestCasesPageProps) {
  const navigate = useNavigate();
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [protocol, setProtocol] = useState<"ui" | "api">("ui");

  // Only "ui" test cases exist until F18 adds API discovery — the toggle is wired
  // for the future protocol but the "api" option stays disabled for now.
  useEffect(() => {
    apiClient.listTestCases(project.id, "pending", protocol).then(setTestCases);
  }, [project.id, protocol]);

  return (
    <Box>
      <ToggleButtonGroup
        value={protocol}
        exclusive
        onChange={(_, value) => value && setProtocol(value)}
        sx={{ mb: 2 }}
      >
        <ToggleButton value="ui">UI</ToggleButton>
        <ToggleButton value="api" disabled>
          API
        </ToggleButton>
      </ToggleButtonGroup>
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

export default function TestCasesPage({ project }: TestCasesPageProps) {
  return (
    <Routes>
      <Route index element={<TestCaseList project={project} />} />
      <Route path=":testCaseId" element={<TestCaseDetail projectId={project.id} />} />
    </Routes>
  );
}
