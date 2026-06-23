import { Drawer, List, ListItemButton, ListItemText, Toolbar } from "@mui/material";
import { NavLink, useLocation } from "react-router-dom";
import { NAV_ITEMS } from "./navItems";

const DRAWER_WIDTH = 220;

export default function NavDrawer() {
  const location = useLocation();

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
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            component={NavLink}
            to={item.path}
            selected={location.pathname === item.path}
          >
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Drawer>
  );
}
