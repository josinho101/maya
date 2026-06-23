import { AppBar, Box, Toolbar, Typography } from "@mui/material";
import { Link } from "react-router-dom";
import HealthStatus from "../components/HealthStatus";

export default function TopBar() {
  return (
    <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
      <Toolbar sx={{ gap: 2 }}>
        <Box
          component={Link}
          to="/projects"
          sx={{
            display: "flex",
            alignItems: "baseline",
            gap: 1,
            flexGrow: 1,
            color: "inherit",
            textDecoration: "none",
          }}
        >
          <Typography variant="h6" noWrap>
            MAYA
          </Typography>
          <Typography variant="caption" color="text.secondary" noWrap>
            Test Automation Framework
          </Typography>
        </Box>
        <Box>
          <HealthStatus />
        </Box>
      </Toolbar>
    </AppBar>
  );
}
