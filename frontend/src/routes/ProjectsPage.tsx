import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import AddIcon from "@mui/icons-material/Add";
import {
  Box,
  Card,
  CardActions,
  CardContent,
  Fab,
  Grid,
  IconButton,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import { apiClient, type Project } from "../api/client";
import ProjectFormDialog from "../components/ProjectFormDialog";
import ConfirmDeleteDialog from "../components/ConfirmDeleteDialog";
import AppBreadcrumbs from "../components/AppBreadcrumbs";

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [dialog, setDialog] = useState<{ mode: "create" | "edit"; project?: Project } | null>(
    null,
  );
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);

  const refresh = () => {
    apiClient.listProjects().then(setProjects);
  };

  useEffect(refresh, []);

  const handleSaved = (project: Project) => {
    setProjects((current) => {
      const exists = current.some((p) => p.id === project.id);
      return exists
        ? current.map((p) => (p.id === project.id ? project : p))
        : [...current, project];
    });
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await apiClient.deleteProject(deleteTarget.id);
    setProjects((current) => current.filter((p) => p.id !== deleteTarget.id));
    setDeleteTarget(null);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Toolbar />
      <AppBreadcrumbs segments={[{ label: "Projects" }]} />
      <Grid container spacing={2}>
        {projects.map((project) => (
          <Grid key={project.id} size={{ xs: 12, sm: 6, md: 3, lg: 2 }}>
            <Card sx={{ width: "100%", minWidth: 0 }}>
              <CardContent
                sx={{ cursor: "pointer", minWidth: 0 }}
                onClick={() => navigate(`/projects/${project.id}`)}
              >
                <Tooltip title={project.name}>
                  <Typography variant="h6" noWrap>
                    {project.name}
                  </Typography>
                </Tooltip>
                <Tooltip title={project.description ?? ""}>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {project.description}
                  </Typography>
                </Tooltip>
              </CardContent>
              <CardActions sx={{ justifyContent: "space-between" }}>
                <IconButton
                  aria-label={`open ${project.name}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/projects/${project.id}`);
                  }}
                >
                  <FolderOpenIcon />
                </IconButton>
                <Box>
                  <IconButton
                    aria-label={`edit ${project.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setDialog({ mode: "edit", project });
                    }}
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    aria-label={`delete ${project.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTarget(project);
                    }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Box>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Fab
        color="primary"
        aria-label="create project"
        sx={{ position: "fixed", bottom: 24, right: 24 }}
        onClick={() => setDialog({ mode: "create" })}
      >
        <AddIcon />
      </Fab>

      <ProjectFormDialog
        open={dialog !== null}
        mode={dialog?.mode ?? "create"}
        project={dialog?.project}
        onClose={() => setDialog(null)}
        onSaved={handleSaved}
      />

      <ConfirmDeleteDialog
        open={deleteTarget !== null}
        title="Delete project"
        message={`Delete "${deleteTarget?.name}"? It will be archived, not removed from disk.`}
        onConfirm={handleDelete}
        onClose={() => setDeleteTarget(null)}
      />
    </Box>
  );
}
