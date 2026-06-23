import { AppBar, Box, Toolbar, Typography } from "@mui/material";
import { Link } from "react-router-dom";
import HealthStatus from "../components/HealthStatus";

export default function TopBar() {
  return (
    <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
      <Toolbar sx={{ gap: 2 }}>
        <Typography
          variant="h6"
          noWrap
          component={Link}
          to="/projects"
          sx={{ flexGrow: 1, color: "inherit", textDecoration: "none" }}
        >
          MAYA
        </Typography>
        <Box>
          <HealthStatus />
        </Box>
      </Toolbar>
    </AppBar>
  );
}
