import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { apiClient, type TestCase, type UIStep } from "../api/client";

interface TestCaseDetailProps {
  projectId: string;
}

function inputToText(input: unknown): string {
  if (input === null || input === undefined) return "";
  return typeof input === "string" ? input : JSON.stringify(input);
}

export default function TestCaseDetail({ projectId }: TestCaseDetailProps) {
  const { testCaseId } = useParams<{ testCaseId: string }>();
  const navigate = useNavigate();
  const [testCase, setTestCase] = useState<TestCase | null>(null);
  const [steps, setSteps] = useState<UIStep[]>([]);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  useEffect(() => {
    if (!testCaseId) return;
    apiClient.listTestCases(projectId, "pending", "ui").then((cases) => {
      const found = cases.find((tc) => tc.id === testCaseId) ?? null;
      setTestCase(found);
      setSteps(found?.protocol === "ui" ? found.steps : []);
    });
  }, [projectId, testCaseId]);

  if (!testCase || !testCaseId) return null;

  const updateStep = (index: number, field: "action" | "strategy" | "value" | "input", text: string) => {
    setSteps((current) =>
      current.map((step, i) => {
        if (i !== index) return step;
        if (field === "action") return { ...step, action: text };
        if (field === "input") return { ...step, input: text };
        return {
          ...step,
          target: {
            strategy: field === "strategy" ? text : step.target?.strategy ?? "",
            value: field === "value" ? text : step.target?.value ?? "",
          },
        };
      }),
    );
  };

  const handleSave = async () => {
    const updated = await apiClient.patchTestCaseSteps(projectId, testCaseId, steps);
    setTestCase(updated);
  };

  const handleApprove = async () => {
    await apiClient.approveTestCase(projectId, testCaseId);
    navigate("..");
  };

  const handleReject = async () => {
    await apiClient.rejectTestCase(projectId, testCaseId, rejectReason);
    setRejectOpen(false);
    navigate("..");
  };

  return (
    <Box>
      <Typography variant="h6">{testCase.id}</Typography>
      <Typography variant="body2" color="text.secondary">
        Created by: {testCase.created_by} · Status: {testCase.status}
      </Typography>

      {testCase.protocol === "ui" && (
        <Box sx={{ mt: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Action</TableCell>
                <TableCell>Locator strategy</TableCell>
                <TableCell>Locator value</TableCell>
                <TableCell>Input</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {steps.map((step, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <TextField
                      size="small"
                      value={step.action}
                      onChange={(e) => updateStep(index, "action", e.target.value)}
                    />
                  </TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      value={step.target?.strategy ?? ""}
                      onChange={(e) => updateStep(index, "strategy", e.target.value)}
                    />
                  </TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      value={step.target?.value ?? ""}
                      onChange={(e) => updateStep(index, "value", e.target.value)}
                    />
                  </TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      value={inputToText(step.input)}
                      onChange={(e) => updateStep(index, "input", e.target.value)}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Button sx={{ mt: 2 }} variant="outlined" onClick={handleSave}>
            Save
          </Button>
        </Box>
      )}

      <Box sx={{ mt: 3, display: "flex", gap: 2 }}>
        <Button variant="contained" color="success" onClick={handleApprove}>
          Approve
        </Button>
        <Button variant="contained" color="error" onClick={() => setRejectOpen(true)}>
          Reject
        </Button>
      </Box>

      <Dialog open={rejectOpen} onClose={() => setRejectOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Reject test case</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Reason"
            fullWidth
            multiline
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectOpen(false)}>Cancel</Button>
          <Button color="error" disabled={!rejectReason.trim()} onClick={handleReject}>
            Reject
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
