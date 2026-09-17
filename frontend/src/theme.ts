import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#2563eb" },
    success: { main: "#16a34a" },
    warning: { main: "#ea580c" },
    background: { default: "#f6f8fc", paper: "#ffffff" }
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans JP", sans-serif',
    h4: { fontWeight: 750 },
    h6: { fontWeight: 700 }
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          border: "1px solid #e5e7eb",
          boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)"
        }
      }
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { textTransform: "none", fontWeight: 700 } }
    }
  }
});
