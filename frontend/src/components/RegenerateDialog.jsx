import { useState, useEffect } from "react";
import {
  Box, Button, Checkbox, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, Divider, FormControlLabel, List, ListItem,
  Alert,
} from "@mui/material";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import RefreshIcon from "@mui/icons-material/Refresh";
import ClosableDialogTitle from "./ClosableDialogTitle";

const METHOD_COLOR = { GET: "info", POST: "success", PUT: "warning", PATCH: "warning", DELETE: "error" };

export default function RegenerateDialog({ open, endpoints, loading, onClose, onConfirm }) {
  const [selected, setSelected] = useState([]);

  useEffect(() => {
    if (endpoints.length) setSelected(endpoints.map((_, i) => i));
  }, [endpoints]);

  const allChecked = selected.length === endpoints.length;
  const noneChecked = selected.length === 0;

  const toggleAll = () => {
    setSelected(allChecked ? [] : endpoints.map((_, i) => i));
  };

  const toggle = (i) => {
    setSelected((prev) =>
      prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i]
    );
  };

  const handleConfirm = () => {
    const chosenEndpoints = selected.map((i) => ({
      endpoint: endpoints[i].endpoint,
      method: endpoints[i].method,
    }));
    // If all endpoints are selected, pass null to signal full regeneration
    const payload = chosenEndpoints.length === endpoints.length ? null : chosenEndpoints;
    onConfirm(payload);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <ClosableDialogTitle onClose={onClose} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <RefreshIcon color="warning" />
        Regenerate Test Cases
      </ClosableDialogTitle>
      <DialogContent>
        <Alert severity="warning" icon={<WarningAmberIcon />} sx={{ mb: 2 }}>
          Previously generated test cases will be cleared for the selected endpoints.
          This action cannot be undone.
        </Alert>

        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
            <CircularProgress size={28} />
          </Box>
        ) : (
          <>
            <FormControlLabel
              control={
                <Checkbox
                  checked={allChecked}
                  indeterminate={!allChecked && !noneChecked}
                  onChange={toggleAll}
                />
              }
              label="Select All"
              sx={{ mb: 0.5 }}
            />
            <Divider sx={{ mb: 1 }} />
            <List dense disablePadding>
              {endpoints.map((ep, i) => (
                <ListItem key={i} disablePadding sx={{ py: 0.25 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selected.includes(i)}
                        onChange={() => toggle(i)}
                        size="small"
                      />
                    }
                    label={
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Chip
                          label={ep.method}
                          size="small"
                          color={METHOD_COLOR[ep.method] || "default"}
                          sx={{ minWidth: 56, fontWeight: 600 }}
                        />
                        <span style={{ fontFamily: "monospace", fontSize: 13 }}>{ep.endpoint}</span>
                      </Box>
                    }
                    sx={{ m: 0, width: "100%" }}
                  />
                </ListItem>
              ))}
            </List>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          color="primary"
          startIcon={<RefreshIcon />}
          onClick={handleConfirm}
          disabled={loading || noneChecked}
        >
          Regenerate
        </Button>
      </DialogActions>
    </Dialog>
  );
}
