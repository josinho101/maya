import type { PaletteMode, PaletteOptions } from "@mui/material";

// Single source of truth for palette mode. A future light/dark toggle only
// needs to replace this constant with state/context — nothing else changes.
export const DEFAULT_PALETTE_MODE: PaletteMode = "dark";

// MUI's own brand/docs dark palette (the same tokens mui.com uses).
export const DIVIDER_COLOR = "rgba(194, 224, 255, 0.08)";

export const palette: PaletteOptions = {
  mode: DEFAULT_PALETTE_MODE,
  primary: {
    light: "#66B2FF",
    main: "#3399FF",
    dark: "#007FFF",
    contrastText: "#fff",
  },
  background: {
    default: "#0A1929",
    paper: "#001E3C",
  },
  divider: DIVIDER_COLOR,
};
