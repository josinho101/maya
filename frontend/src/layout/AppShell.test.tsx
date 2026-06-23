import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import theme from "../theme/theme";
import AppShell from "./AppShell";
import { apiClient } from "../api/client";

vi.mock("../api/client", () => ({
  apiClient: {
    getHealth: vi.fn(),
    listProjects: vi.fn(),
    getProject: vi.fn(),
  },
}));

function renderAt(path: string) {
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter initialEntries={[path]}>
        <AppShell />
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe("AppShell", () => {
  beforeEach(() => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({ status: "ok" });
    vi.mocked(apiClient.listProjects).mockResolvedValue([]);
  });

  it("renders the dashboard with no project-scoped navigation at /projects", async () => {
    renderAt("/projects");

    expect(await screen.findByLabelText("create project")).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "primary navigation" }),
    ).not.toBeInTheDocument();
  });

  it("renders the project-scoped drawer at /projects/:id/environments", async () => {
    vi.mocked(apiClient.getProject).mockResolvedValue({
      id: "acme",
      name: "Acme",
      description: null,
      archived: false,
      created_at: "2026-06-22T00:00:00Z",
      test_types: ["ui"],
      default_environment: "dev",
      environments: [],
    });

    renderAt("/projects/acme/environments");

    const nav = await screen.findByRole("navigation", { name: "primary navigation" });
    ["Environments", "Test Cases", "Runs", "Healing", "Notifications"].forEach((label) => {
      expect(within(nav).getByText(label)).toBeInTheDocument();
    });
  });
});
