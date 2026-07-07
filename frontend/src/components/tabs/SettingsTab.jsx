import { useState, useEffect } from "react";
import {
  Box, Typography, Button, CircularProgress, Alert,
  TextField, Chip, Select, MenuItem, FormControl, InputLabel, Tabs, Tab,
} from "@mui/material";
import { getSettings, saveSettings, testAuthConfig } from "../../api/client";

export default function SettingsTab({ environments, projectId, isAdmin, gen }) {
  const [settingsEnvId, setSettingsEnvId] = useState("");
  const [settingsSubTab, setSettingsSubTab] = useState("authentication");
  const [authDraft, setAuthDraft] = useState(null);
  const [authSaving, setAuthSaving] = useState(false);
  const [authSaveError, setAuthSaveError] = useState("");
  const [authTesting, setAuthTesting] = useState(false);
  const [authTestResult, setAuthTestResult] = useState(null);
  const [customEndpointText, setCustomEndpointText] = useState("");
  const [endpointIsCustom, setEndpointIsCustom] = useState(false);

  useEffect(() => {
    setSettingsEnvId((prev) => (environments.some((e) => e.id === prev) ? prev : environments[0]?.id || ""));
  }, [environments]);

  const results = gen?.testcases?.results || [];
  const postEndpoints = results.filter((r) => r.method === "POST").map((r) => r.endpoint);
  const settingsEnvBaseUrl = (environments.find((e) => e.id === settingsEnvId)?.url || "").replace(/\/$/, "");

  const endpointSelectValue = (() => {
    if (!authDraft) return "";
    if (endpointIsCustom) return "custom";
    const ep = authDraft.auth_endpoint || "";
    if (!ep) return "";
    const path = settingsEnvBaseUrl && ep.startsWith(settingsEnvBaseUrl) ? ep.slice(settingsEnvBaseUrl.length) : ep;
    return postEndpoints.includes(path) ? path : "custom";
  })();

  useEffect(() => {
    if (!settingsEnvId) return;
    setAuthDraft(null);
    setAuthTestResult(null);
    setAuthSaveError("");
    setEndpointIsCustom(false);
    getSettings(projectId, settingsEnvId)
      .then((data) => {
        let cfg = data.auth || {};
        try {
          cfg = { ...cfg, request_body_template: JSON.stringify(JSON.parse(cfg.request_body_template), null, 2) };
        } catch { /* not valid JSON — leave as-is */ }
        const baseUrl = (environments.find((e) => e.id === settingsEnvId)?.url || "").replace(/\/$/, "");
        const ep = cfg.auth_endpoint || "";
        if (postEndpoints.includes(ep) && baseUrl) {
          cfg = { ...cfg, auth_endpoint: baseUrl + ep };
        }
        const fullEp = cfg.auth_endpoint || "";
        const isSwaggerUrl = baseUrl && postEndpoints.some((p) => fullEp === baseUrl + p);
        const isCustom = !!fullEp && !isSwaggerUrl;
        setEndpointIsCustom(isCustom);
        setCustomEndpointText(isCustom ? fullEp : "");
        setAuthDraft(cfg);
      })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settingsEnvId, projectId]);

  const handleAuthSave = async () => {
    setAuthSaveError("");
    setAuthTestResult(null);
    if (authDraft.auth_type === "bearer_login") {
      const tpl = authDraft.request_body_template || "";
      if (!tpl.includes("{{username}}") || !tpl.includes("{{password}}")) {
        setAuthSaveError("Request body template must contain {{username}} and {{password}} placeholders.");
        return;
      }
    }
    try {
      setAuthSaving(true);
      const saved = await saveSettings(projectId, settingsEnvId, { auth: authDraft });
      setAuthDraft(saved.auth);
    } catch (e) {
      setAuthSaveError(e.response?.data?.error || "Failed to save auth config");
    } finally {
      setAuthSaving(false);
    }
  };

  const handleAuthTest = async () => {
    setAuthTestResult(null);
    const triggeredEndpoint = authDraft.auth_endpoint;
    try {
      setAuthTesting(true);
      const result = await testAuthConfig(projectId, settingsEnvId, authDraft);
      setAuthTestResult({ ...result, triggered_endpoint: triggeredEndpoint });
    } catch (e) {
      setAuthTestResult({ success: false, message: e.response?.data?.error || "Request failed", triggered_endpoint: triggeredEndpoint });
    } finally {
      setAuthTesting(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 3 }}>
        <Typography variant="body2" fontWeight={500}>Environment:</Typography>
        {environments.length > 0 ? (
          <Select
            size="small"
            value={settingsEnvId}
            onChange={(e) => {
              setSettingsEnvId(e.target.value);
              setAuthTestResult(null);
              setAuthSaveError("");
            }}
            sx={{ minWidth: 180 }}
          >
            {environments.map((env) => (
              <MenuItem key={env.id} value={env.id}>{env.name}</MenuItem>
            ))}
          </Select>
        ) : (
          <Typography color="text.secondary" variant="body2">
            No environments configured yet — add one in the Environments tab first.
          </Typography>
        )}
      </Box>

      {environments.length > 0 && (
        <Box>
          <Tabs
            value={settingsSubTab}
            onChange={(_, v) => setSettingsSubTab(v)}
            sx={{
              borderBottom: 1,
              borderColor: "divider",
              minHeight: 36,
              "& .MuiTab-root": { minHeight: 34, py: 0.5, px: 2, textTransform: "none", fontSize: 14 },
            }}
          >
            <Tab label="Authentication" value="authentication" />
            <Tab label="Auto Trigger" value="auto_trigger" />
          </Tabs>

          {settingsSubTab === "authentication" && (
            <Box sx={{ pt: 2, bgcolor: "background.paper", p: 2 }}>
              {isAdmin && (
                <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
                  <Button
                    variant="contained"
                    onClick={handleAuthSave}
                    disabled={authSaving || authDraft === null}
                    startIcon={authSaving ? <CircularProgress size={14} /> : null}
                    sx={{ minWidth: 88 }}
                  >
                    Save
                  </Button>
                </Box>
              )}

              {authDraft === null ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                  <CircularProgress size={28} />
                </Box>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
                  <Box sx={{ display: "flex", gap: 2 }}>
                    <FormControl size="small" sx={{ flex: 1 }}>
                      <InputLabel>Auth Type</InputLabel>
                      <Select
                        label="Auth Type"
                        value={authDraft.auth_type}
                        onChange={(e) => {
                          setAuthDraft((d) => ({ ...d, auth_type: e.target.value }));
                          setAuthTestResult(null);
                          setAuthSaveError("");
                        }}
                      >
                        <MenuItem value="none">No Auth</MenuItem>
                        <MenuItem value="bearer_login">Bearer Token</MenuItem>
                      </Select>
                    </FormControl>
                    <FormControl size="small" sx={{ flex: 1 }} disabled={authDraft.auth_type !== "bearer_login"}>
                      <InputLabel>Auth Endpoint</InputLabel>
                      <Select
                        label="Auth Endpoint"
                        value={endpointSelectValue}
                        onChange={(e) => {
                          const val = e.target.value;
                          setAuthTestResult(null);
                          if (val === "custom") {
                            setEndpointIsCustom(true);
                            setAuthDraft((d) => ({ ...d, auth_endpoint: customEndpointText }));
                          } else {
                            setEndpointIsCustom(false);
                            setCustomEndpointText("");
                            const baseUrl = (environments.find((env) => env.id === settingsEnvId)?.url || "").replace(/\/$/, "");
                            setAuthDraft((d) => ({ ...d, auth_endpoint: baseUrl + val }));
                          }
                        }}
                      >
                        {postEndpoints.map((ep) => (
                          <MenuItem key={ep} value={ep} sx={{ fontFamily: "monospace", fontSize: 13 }}>
                            {ep}
                          </MenuItem>
                        ))}
                        <MenuItem value="custom" sx={{ fontStyle: "italic" }}>Custom</MenuItem>
                      </Select>
                    </FormControl>
                  </Box>

                  {authDraft.auth_type === "bearer_login" && endpointIsCustom && (
                    <TextField
                      label="Custom Auth Endpoint"
                      size="small"
                      fullWidth
                      placeholder="https://your-api.com/auth/login"
                      value={customEndpointText}
                      onChange={(e) => {
                        setCustomEndpointText(e.target.value);
                        setAuthDraft((d) => ({ ...d, auth_endpoint: e.target.value }));
                      }}
                    />
                  )}

                  {authDraft.auth_type === "bearer_login" && (
                    <>
                      <TextField
                        label="Request Body Template"
                        size="small"
                        fullWidth
                        multiline
                        rows={5}
                        value={authDraft.request_body_template}
                        onChange={(e) => setAuthDraft((d) => ({ ...d, request_body_template: e.target.value }))}
                        inputProps={{ style: { fontFamily: "monospace", fontSize: 13 } }}
                        helperText="Use {{username}} and {{password}} as placeholders — JSON key names can be anything your API expects"
                      />

                      <Box>
                        <Box sx={{ display: "flex", gap: 1.5, alignItems: "center" }}>
                          <TextField
                            label="Token Path in Response"
                            size="small"
                            value={authDraft.token_path}
                            onChange={(e) => setAuthDraft((d) => ({ ...d, token_path: e.target.value }))}
                            sx={{ minWidth: 300 }}
                          />
                          {isAdmin && (
                            <Button
                              variant="outlined"
                              onClick={handleAuthTest}
                              disabled={authTesting}
                              startIcon={authTesting ? <CircularProgress size={14} /> : null}
                              sx={{ minWidth: 80 }}
                            >
                              Test
                            </Button>
                          )}
                        </Box>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5, ml: 0.25 }}>
                          Dot-separated path, e.g. &quot;token&quot; or &quot;data.access_token&quot;
                        </Typography>
                      </Box>
                    </>
                  )}

                  {authTestResult && (
                    <Box
                      sx={{
                        border: 2,
                        borderColor: authTestResult.success ? "success.main" : "error.main",
                        borderRadius: 1,
                        p: 1.5,
                      }}
                    >
                      {authTestResult.triggered_endpoint && (
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                          <Chip label="POST" size="small" color="success" />
                          <Typography variant="body2" sx={{ fontFamily: "monospace", wordBreak: "break-all" }}>
                            {authTestResult.triggered_endpoint}
                          </Typography>
                        </Box>
                      )}
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                        {authTestResult.status_code != null && (
                          <Chip
                            label={`HTTP ${authTestResult.status_code}`}
                            size="small"
                            color={authTestResult.success ? "success" : "error"}
                          />
                        )}
                        <Typography variant="body2">{authTestResult.message}</Typography>
                      </Box>
                      {authTestResult.response_body != null && (
                        <>
                          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                            Full API Response:
                          </Typography>
                          <Box
                            sx={{
                              fontFamily: "monospace",
                              fontSize: 12,
                              whiteSpace: "pre-wrap",
                              overflowX: "auto",
                              bgcolor: "action.hover",
                              p: 1,
                              borderRadius: 0.5,
                              maxHeight: 260,
                              overflowY: "auto",
                            }}
                          >
                            {typeof authTestResult.response_body === "string"
                              ? authTestResult.response_body
                              : JSON.stringify(authTestResult.response_body, null, 2)}
                          </Box>
                        </>
                      )}
                    </Box>
                  )}

                  {authSaveError && <Alert severity="error">{authSaveError}</Alert>}
                </Box>
              )}
            </Box>
          )}

          {settingsSubTab === "auto_trigger" && (
            <Box sx={{ pt: 2, bgcolor: "background.paper", p: 2 }}>
              {isAdmin && (
                <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
                  <Button variant="contained" disabled>Save</Button>
                </Box>
              )}
              <Typography color="text.secondary" variant="body2">
                Auto trigger configuration coming soon.
              </Typography>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}
