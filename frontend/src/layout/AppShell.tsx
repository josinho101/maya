import { Box, Toolbar } from "@mui/material";
import { Navigate, Route, Routes } from "react-router-dom";
import TopBar from "./TopBar";
import NavDrawer from "./NavDrawer";
import ProjectsPage from "../routes/ProjectsPage";
import TestCasesPage from "../routes/TestCasesPage";
import RunsPage from "../routes/RunsPage";
import HealingPage from "../routes/HealingPage";
import NotificationsPage from "../routes/NotificationsPage";

export default function AppShell() {
  return (
    <Box sx={{ display: "flex" }}>
      <TopBar />
      <NavDrawer />
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/test-cases" element={<TestCasesPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/healing" element={<HealingPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
        </Routes>
      </Box>
    </Box>
  );
}
