import { createTheme } from "@mui/material/styles";
import { DIVIDER_COLOR, palette } from "./palette";

const theme = createTheme({
  palette,
  shape: {
    borderRadius: 10,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: palette.background?.paper,
          borderBottom: `1px solid ${DIVIDER_COLOR}`,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: `1px solid ${DIVIDER_COLOR}`,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundImage: "none",
          borderRight: `1px solid ${DIVIDER_COLOR}`,
        },
      },
    },
  },
});

export default theme;
