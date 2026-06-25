import { useState, useEffect, useCallback, useRef } from "react";
import {
  Box, Typography, Button, ButtonGroup, Card, CardContent, CircularProgress,
  Alert, Chip, Table, TableBody, TableCell, TableHead, TableRow,
  IconButton, Tooltip, LinearProgress,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import LinkIcon from "@mui/icons-material/Link";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RefreshIcon from "@mui/icons-material/Refresh";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { useNavigate, useParams } from "react-router-dom";
import {
  getProject, uploadSwagger, importSwaggerFromUrl, triggerGeneration, getGeneration,
  listGenerations, listExecutions, getReportUrl,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusChip from "../components/StatusChip";
import RegenerateDialog from "../components/RegenerateDialog";
import ExecutionCharts from "../components/ExecutionCharts";

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const nav = useNavigate();
  const fileRef = useRef();
  const { isAdmin } = useAuth();

  const [project, setProject] = useState(null);
  const [generations, setGenerations] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);

  // URL import dialog state
  const [urlDialogOpen, setUrlDialogOpen] = useState(false);
  const [swaggerUrl, setSwaggerUrl] = useState("");

  // Regenerate dialog state
  const [regenOpen, setRegenOpen] = useState(false);
  const [regenEndpoints, setRegenEndpoints] = useState([]);
  const [regenLoading, setRegenLoading] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      const [proj, gens, execs] = await Promise.all([
        getProject(projectId),
        listGenerations(projectId),
        listExecutions(projectId),
      ]);
      setProject(proj);
      setGenerations(gens);
      setExecutions(execs);
    } catch {
      setError("Failed to load project");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setUploading(true);
      setError("");
      await uploadSwagger(projectId, file);
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.error || "Upload failed");
    } finally {
      setUploading(false);
      fileRef.current.value = "";
    }
  };

  const handleImportFromUrl = async () => {
    if (!swaggerUrl.trim()) return;
    try {
      setUploading(true);
      setError("");
      await importSwaggerFromUrl(projectId, swaggerUrl.trim());
      setUrlDialogOpen(false);
      setSwaggerUrl("");
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.error || "Import failed");
    } finally {
      setUploading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError("");
      const res = await triggerGeneration(projectId);
      if (!res?.generation_id) throw new Error("Invalid response from server");
      nav(`/projects/${projectId}/generations/${res.generation_id}`);
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Failed to trigger generation");
      setGenerating(false);
    }
  };

  const handleViewTestCases = () => {
    const latestGen = generations.find((g) => ["REVIEW", "APPROVED"].includes(g.status));
    if (latestGen) nav(`/projects/${projectId}/generations/${latestGen.id}`);
  };

  const handleOpenRegenerate = async () => {
    setRegenOpen(true);
    setRegenLoading(true);
    try {
      // Get endpoint list from the most recent generation that has test cases
      const latestGen = generations.find((g) => ["REVIEW", "APPROVED"].includes(g.status));
      if (latestGen) {
        const genData = await getGeneration(projectId, latestGen.id);
        const endpoints = (genData.testcases?.results || []).map((r) => ({
          endpoint: r.endpoint,
          method: r.method,
        }));
        setRegenEndpoints(endpoints);
      }
    } catch {
      setError("Failed to load endpoint list");
      setRegenOpen(false);
    } finally {
      setRegenLoading(false);
    }
  };

  const handleRegenerateConfirm = async (endpointsToRegenerate) => {
    setRegenOpen(false);
    try {
      setGenerating(true);
      setError("");
      // null means regenerate all; array means regenerate subset
      const body = endpointsToRegenerate !== null ? { endpoints_to_regenerate: endpointsToRegenerate } : {};
      const res = await triggerGeneration(projectId, body);
      if (!res?.generation_id) throw new Error("Invalid response from server");
      nav(`/projects/${projectId}/generations/${res.generation_id}`);
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Failed to trigger regeneration");
      setGenerating(false);
    }
  };

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}><CircularProgress /></Box>;
  if (!project) return <Alert severity="error">Project not found</Alert>;

  const swagger = project.swagger;
  const hasTestCases = generations.some((g) => ["REVIEW", "APPROVED"].includes(g.status));
  const activeGen = generations.find((g) => ["PENDING", "GENERATING"].includes(g.status));

  return (
    <Box>
      {/* Compact page header */}
      <Box sx={{ mb: 1.5 }}>
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, flexDirection: { xs: "column", md: "row" } }}>

          {/* Left: back nav + title + description */}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <IconButton size="small" onClick={() => nav("/projects")}>
                <ArrowBackIcon fontSize="small" />
              </IconButton>
              <Typography variant="h5" fontWeight={700}>{project.name}</Typography>
            </Box>
            {project.description && (
              <Typography variant="body2" color="text.secondary" sx={{ ml: 4.5, mt: 0.25 }}>
                {project.description}
              </Typography>
            )}
          </Box>

          {/* Right: upload actions + conditional test case buttons + metadata chips below */}
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 0.75, flexShrink: 0 }}>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center", justifyContent: "flex-end" }}>
            {isAdmin && (
              <>
                <input
                  type="file" accept=".yaml,.yml,.json" ref={fileRef}
                  style={{ display: "none" }} onChange={handleUpload}
                />
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Typography variant="caption" color="text.secondary">Upload Swagger</Typography>
                  <ButtonGroup size="small" variant="outlined" disabled={uploading}>
                    <Tooltip title={swagger ? "Re-upload Swagger" : "Upload Swagger"}>
                      <Button onClick={() => fileRef.current.click()}>
                        {uploading ? <CircularProgress size={14} /> : <UploadFileIcon fontSize="small" />}
                      </Button>
                    </Tooltip>
                    <Tooltip title="Import from URL">
                      <Button onClick={() => setUrlDialogOpen(true)}>
                        <LinkIcon fontSize="small" />
                      </Button>
                    </Tooltip>
                  </ButtonGroup>
                </Box>
              </>
            )}
            {swagger && !hasTestCases && !activeGen && !generating && isAdmin && (
              <Button variant="contained" size="small" startIcon={<PlayArrowIcon />} onClick={handleGenerate}>
                Generate Test Cases
              </Button>
            )}
            {swagger && hasTestCases && (
              <Button variant="outlined" size="small" startIcon={<OpenInNewIcon />} onClick={handleViewTestCases}>
                View Test Cases
              </Button>
            )}
            {swagger && (activeGen || generating) && (
              <Button
                variant="outlined" color="warning" size="small"
                startIcon={<CircularProgress size={16} />}
                onClick={activeGen ? () => nav(`/projects/${projectId}/generations/${activeGen.id}`) : undefined}
                disabled={!activeGen}
              >
                View Progress
              </Button>
            )}
            {swagger && hasTestCases && isAdmin && !activeGen && !generating && (
              <Button variant="contained" color="warning" size="small" startIcon={<RefreshIcon />} onClick={handleOpenRegenerate}>
                Regenerate Test Cases
              </Button>
            )}
            </Box>
            {swagger && (
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", justifyContent: "flex-end", mt: 0.5 }}>
                {swagger.base_url && (
                  <Chip label={swagger.base_url} size="small" variant="outlined" color="secondary" />
                )}
                {swagger.endpoint_count != null && (
                  <Chip label={`${swagger.endpoint_count} endpoints`} color="primary" size="small" />
                )}
                {swagger.uploaded_at && !isNaN(new Date(swagger.uploaded_at)) && (
                  <Typography variant="caption" color="text.secondary" sx={{ alignSelf: "center" }}>
                    Uploaded {new Date(swagger.uploaded_at).toLocaleString()}
                  </Typography>
                )}
              </Box>
            )}
          </Box>
        </Box>
        {uploading && <LinearProgress sx={{ mt: 1 }} />}
        {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
      </Box>

      <Box sx={{ mt: 3 }}>
        <ExecutionCharts executions={executions} />
      </Box>

      {/* Executions */}
      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight={600} gutterBottom>Executions</Typography>
          {executions.length === 0 ? (
            <Typography color="text.secondary">No executions yet</Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Pass</TableCell>
                  <TableCell>Fail</TableCell>
                  <TableCell>Rate</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {executions.map((e) => (
                  <TableRow key={e.id} hover>
                    <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{e.id}</TableCell>
                    <TableCell><StatusChip status={e.status} /></TableCell>
                    <TableCell sx={{ color: "success.main" }}>{e.summary?.passed ?? "—"}</TableCell>
                    <TableCell sx={{ color: "error.main" }}>{e.summary?.failed ?? "—"}</TableCell>
                    <TableCell>
                      {e.summary ? `${e.summary.success_rate}%` : "—"}
                    </TableCell>
                    <TableCell>{new Date(e.started_at).toLocaleString()}</TableCell>
                    <TableCell align="right">
                      <Button size="small" onClick={() => nav(`/projects/${projectId}/executions/${e.id}`)}>
                        View
                      </Button>
                      {e.status === "COMPLETED" && (
                        <Tooltip title="Open HTML report">
                          <IconButton size="small" onClick={() => window.open(getReportUrl(projectId, e.id), "_blank")}>
                            <OpenInNewIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={urlDialogOpen}
        onClose={() => { setUrlDialogOpen(false); setSwaggerUrl(""); }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Import from URL</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="URL"
            placeholder="https://example.com/openapi.json"
            value={swaggerUrl}
            onChange={(e) => setSwaggerUrl(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleImportFromUrl(); }}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setUrlDialogOpen(false); setSwaggerUrl(""); }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleImportFromUrl}
            disabled={uploading || !swaggerUrl.trim()}
            startIcon={uploading ? <CircularProgress size={16} /> : null}
          >
            Import
          </Button>
        </DialogActions>
      </Dialog>

      <RegenerateDialog
        open={regenOpen}
        endpoints={regenEndpoints}
        loading={regenLoading}
        onClose={() => setRegenOpen(false)}
        onConfirm={handleRegenerateConfirm}
      />
    </Box>
  );
}
