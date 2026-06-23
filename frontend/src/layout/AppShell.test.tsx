import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import theme from "../theme/theme";
import AppShell from "./AppShell";
import { NAV_ITEMS } from "./navItems";

describe("AppShell", () => {
  it("renders every nav item", () => {
    render(
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          <AppShell />
        </MemoryRouter>
      </ThemeProvider>,
    );

    const nav = within(screen.getByRole("navigation", { name: "primary navigation" }));
    NAV_ITEMS.forEach((item) => {
      expect(nav.getByText(item.label)).toBeInTheDocument();
    });
  });
});
