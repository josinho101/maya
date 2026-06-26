import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#7C4DFF" },
    secondary: { main: "#00BCD4" },
    success: { main: "#66BB6A" },
    error: { main: "#EF5350" },
    warning: { main: "#FFA726" },
    background: {
      default: "#0D0D0D",
      paper: "#1A1A2E",
    },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Inter", "Roboto", sans-serif',
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: { backgroundImage: "none" },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { backgroundImage: "none" },
      },
    },
    MuiDialogActions: {
      styleOverrides: {
        root: { padding: "16px 24px" },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600,
          paddingLeft: 20,
          paddingRight: 20,
        },
        outlined: { boxShadow: "none" },
        text: { boxShadow: "none" },
      },
    },
  },
});

export default theme;
