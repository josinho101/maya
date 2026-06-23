import { useEffect, useState } from "react";
import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  FormGroup,
  TextField,
  Typography,
} from "@mui/material";
import { ApiError, apiClient, type Project, type TestType } from "../api/client";

interface ProjectFormDialogProps {
  open: boolean;
  mode: "create" | "edit";
  project?: Project;
  onClose: () => void;
  onSaved: (project: Project) => void;
}

export default function ProjectFormDialog({
  open,
  mode,
  project,
  onClose,
  onSaved,
}: ProjectFormDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [testTypes, setTestTypes] = useState<TestType[]>(["ui"]);
  const [saving, setSaving] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setName(project?.name ?? "");
    setDescription(project?.description ?? "");
    setTestTypes(project?.test_types ?? ["ui"]);
    setNameError(null);
  }, [open, project]);

  const canSave = name.trim().length > 0 && testTypes.length > 0;

  const toggleTestType = (testType: TestType) => {
    setTestTypes((current) =>
      current.includes(testType)
        ? current.filter((t) => t !== testType)
        : [...current, testType],
    );
  };

  const handleSave = async () => {
    setSaving(true);
    setNameError(null);
    try {
      const saved =
        mode === "create"
          ? await apiClient.createProject({
              name,
              description: description || null,
              test_types: testTypes,
            })
          : await apiClient.updateProject(project!.id, {
              name,
              description: description || null,
              test_types: testTypes,
            });
      onSaved(saved);
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setNameError(err.detail ?? "A project with this name already exists.");
      } else {
        throw err;
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{mode === "create" ? "Create Project" : "Edit Project"}</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <TextField
          label="Name"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setNameError(null);
          }}
          error={nameError !== null}
          helperText={nameError ?? "Choose a different name if it's already in use."}
          fullWidth
        />
        <TextField
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          multiline
          minRows={2}
          fullWidth
        />
        <Typography variant="subtitle2">What kind of testing does this project need?</Typography>
        <FormGroup>
          <FormControlLabel
            control={
              <Checkbox checked={testTypes.includes("ui")} onChange={() => toggleTestType("ui")} />
            }
            label="UI testing"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={testTypes.includes("api")}
                onChange={() => toggleTestType("api")}
              />
            }
            label="API testing"
          />
        </FormGroup>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={!canSave || saving} onClick={handleSave}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}
