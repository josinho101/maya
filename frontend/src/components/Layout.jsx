import { Box, AppBar, Toolbar, Typography, IconButton, Tooltip } from "@mui/material";
import BugReportIcon from "@mui/icons-material/BugReport";
import LogoutIcon from "@mui/icons-material/Logout";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  const handleLogout = () => {
    logout();
    nav("/login", { replace: true });
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <AppBar position="static" elevation={0} sx={{ borderBottom: "1px solid #2A2A4A" }}>
        <Toolbar variant="dense">
          <Box
            sx={{ display: "flex", alignItems: "center", cursor: "pointer" }}
            onClick={() => nav("/projects")}
          >
            <BugReportIcon sx={{ mr: 1.5, color: "warning.main" }} />
            <Typography variant="h6" fontWeight={700} letterSpacing={1}>
              MAYA
            </Typography>
            <Typography variant="caption" sx={{ ml: 1, color: "text.secondary" }}>
              Test Automation Platform
            </Typography>
          </Box>

          <Box sx={{ ml: "auto", display: "flex", alignItems: "center", gap: 1.5 }}>
            {user && (
              <>
                <Typography variant="body2" color="text.secondary" sx={{ display: { xs: "none", sm: "block" } }}>
                  Hello, {user.username.charAt(0).toUpperCase() + user.username.slice(1)}
                </Typography>
                <Tooltip title="Sign out">
                  <IconButton size="small" onClick={handleLogout} color="inherit">
                    <LogoutIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </>
            )}
          </Box>
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ flex: 1, p: { xs: 1.5, md: 2 }, maxWidth: 1400, mx: "auto", width: "100%" }}>
        {children}
      </Box>
    </Box>
  );
}
