import { Drawer, List, ListItemButton, ListItemText, Toolbar } from "@mui/material";
import { NavLink, useLocation } from "react-router-dom";
import { buildProjectNavItems } from "./navItems";

const DRAWER_WIDTH = 220;

interface ProjectDrawerProps {
  projectId: string;
}

export default function ProjectDrawer({ projectId }: ProjectDrawerProps) {
  const location = useLocation();
  const items = buildProjectNavItems(projectId);

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH, boxSizing: "border-box" },
      }}
    >
      <Toolbar />
      <List component="nav" aria-label="primary navigation">
        {items.map((item) => (
          <ListItemButton
            key={item.path}
            component={NavLink}
            to={item.path}
            selected={location.pathname.startsWith(item.path)}
          >
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Drawer>
  );
}
