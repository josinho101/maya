import { Navigate, Route, Routes } from "react-router-dom";
import TopBar from "./TopBar";
import ProjectsPage from "../routes/ProjectsPage";
import ProjectDetail from "../routes/ProjectDetail";

export default function AppShell() {
  return (
    <>
      <TopBar />
      <Routes>
        <Route path="/" element={<Navigate to="/projects" replace />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:projectId/*" element={<ProjectDetail />} />
      </Routes>
    </>
  );
}
