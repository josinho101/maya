import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";
import { Box, Link as MuiLink, Toolbar, Typography } from "@mui/material";
import { apiClient, type Project } from "../api/client";
import ProjectDrawer from "../layout/ProjectDrawer";
import { buildProjectNavItems } from "../layout/navItems";
import AppBreadcrumbs, { type BreadcrumbSegment } from "../components/AppBreadcrumbs";
import EnvironmentsPanel from "./EnvironmentsPanel";
import TestCasesPage from "./TestCasesPage";
import RunsPage from "./RunsPage";
import HealingPage from "./HealingPage";
import NotificationsPage from "./NotificationsPage";

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const location = useLocation();
  const [project, setProject] = useState<Project | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    setProject(null);
    setNotFound(false);
    apiClient
      .getProject(projectId)
      .then(setProject)
      .catch(() => setNotFound(true));
  }, [projectId]);

  if (!projectId) return null;

  if (notFound) {
    return (
      <Box sx={{ p: 3 }}>
        <Toolbar />
        <Typography variant="h5">Project not found</Typography>
        <MuiLink component={Link} to="/projects">
          Back to dashboard
        </MuiLink>
      </Box>
    );
  }

  if (!project) return null;

  const navItems = buildProjectNavItems(projectId);
  const currentSection = navItems.find((item) => location.pathname.startsWith(item.path));
  const envId = location.pathname.match(/\/environments\/([^/]+)/)?.[1];
  const testCaseId = location.pathname.match(/\/test-cases\/([^/]+)/)?.[1];
  const detailId = envId ?? testCaseId;

  const breadcrumbSegments: BreadcrumbSegment[] = [
    { label: "Projects", to: "/projects" },
    { label: project.name, to: currentSection ? currentSection.path : undefined },
    ...(currentSection
      ? [{ label: currentSection.label, to: detailId ? currentSection.path : undefined }]
      : []),
    ...(detailId ? [{ label: detailId }] : []),
  ];

  return (
    <Box sx={{ display: "flex" }}>
      <ProjectDrawer projectId={projectId} />
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <AppBreadcrumbs segments={breadcrumbSegments} />
        <Routes>
          <Route index element={<Navigate to="environments" replace />} />
          <Route path="environments/*" element={<EnvironmentsPanel project={project} />} />
          <Route path="test-cases/*" element={<TestCasesPage project={project} />} />
          <Route path="runs/*" element={<RunsPage project={project} />} />
          <Route path="healing" element={<HealingPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Routes>
      </Box>
    </Box>
  );
}
