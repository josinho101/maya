import { ThemeProvider, CssBaseline } from "@mui/material";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import theme from "./theme";
import { AuthProvider } from "./context/AuthContext";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import GenerationPage from "./pages/GenerationPage";
import ExecutionPage from "./pages/ExecutionPage";

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Routes>
                      <Route path="/" element={<Navigate to="/projects" replace />} />
                      <Route path="/projects" element={<ProjectsPage />} />
                      <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
                      <Route
                        path="/projects/:projectId/generations/:genId"
                        element={<GenerationPage />}
                      />
                      <Route
                        path="/projects/:projectId/executions/:execId"
                        element={<ExecutionPage />}
                      />
                    </Routes>
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
