import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { apiClient, type HealingEventLogEntry, type TestCase } from "../api/client";

interface HealingDetailProps {
  projectId: string;
}

function locatorText(locator: { strategy: string; value: string } | null): string {
  return locator ? `${locator.strategy}=${locator.value}` : "—";
}

export default function HealingDetail({ projectId }: HealingDetailProps) {
  const { testCaseId } = useParams<{ testCaseId: string }>();
  const navigate = useNavigate();
  const [testCase, setTestCase] = useState<TestCase | null>(null);
  const [entries, setEntries] = useState<HealingEventLogEntry[]>([]);

  const reload = () => {
    if (!testCaseId) return;
    apiClient.listTestCases(projectId, "needs_review", "ui").then((cases) => {
      setTestCase(cases.find((tc) => tc.id === testCaseId) ?? null);
    });
    apiClient.getHealingLog(projectId, testCaseId).then(setEntries);
  };

  useEffect(reload, [projectId, testCaseId]);

  if (!testCaseId) return null;

  const resolve = async (healId: string, action: "accept" | "reject") => {
    await apiClient.resolveHealing(healId, action);
    reload();
    if (action === "accept") navigate("..");
  };

  return (
    <Box>
      <Typography variant="h6">{testCaseId}</Typography>
      {testCase?.protocol === "ui" && (
        <Typography variant="body2" color="text.secondary">
          View: {testCase.view_identity} · Status: {testCase.status}
        </Typography>
      )}

      <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
        {entries.map((entry) => {
          const best = entry.candidates[0] ?? null;
          const failureScreenshot = apiClient.getScreenshotUrl(entry.run_id, `${testCaseId}_${entry.step_id}.png`);
          const visionScreenshot = entry.escalated_to_vision
            ? apiClient.getScreenshotUrl(entry.run_id, `heal_${entry.heal_id}.png`)
            : null;

          return (
            <Card key={entry.heal_id} variant="outlined">
              <CardContent>
                <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 1 }}>
                  <Chip size="small" label={entry.failure_type} />
                  {entry.auto_applied && <Chip size="small" color="success" label="auto-applied" />}
                  {entry.resolution && <Chip size="small" color="info" label={entry.resolution} />}
                </Box>

                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Before</TableCell>
                      <TableCell>After (best candidate)</TableCell>
                      <TableCell>Confidence</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell>{locatorText(entry.original_locator)}</TableCell>
                      <TableCell>{best ? locatorText(best) : "—"}</TableCell>
                      <TableCell>{best ? best.confidence.toFixed(2) : "—"}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>

                <Box sx={{ display: "flex", gap: 2, mt: 2 }}>
                  <Box>
                    <Typography variant="caption">Failure screenshot</Typography>
                    <Box
                      component="img"
                      src={failureScreenshot}
                      alt="failure"
                      sx={{ maxWidth: 320, display: "block", border: "1px solid #ddd" }}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  </Box>
                  {visionScreenshot && (
                    <Box>
                      <Typography variant="caption">Vision-tier screenshot</Typography>
                      <Box
                        component="img"
                        src={visionScreenshot}
                        alt="vision tier"
                        sx={{ maxWidth: 320, display: "block", border: "1px solid #ddd" }}
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none";
                        }}
                      />
                    </Box>
                  )}
                </Box>

                {!entry.auto_applied && !entry.resolution && best && (
                  <Box sx={{ display: "flex", gap: 2, mt: 2 }}>
                    <Button variant="contained" color="success" onClick={() => resolve(entry.heal_id, "accept")}>
                      Accept
                    </Button>
                    <Button variant="outlined" color="error" onClick={() => resolve(entry.heal_id, "reject")}>
                      Reject
                    </Button>
                  </Box>
                )}
              </CardContent>
            </Card>
          );
        })}
      </Box>
    </Box>
  );
}
