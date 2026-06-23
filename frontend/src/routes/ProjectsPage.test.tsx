import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import theme from "../theme/theme";
import ProjectsPage from "./ProjectsPage";
import { apiClient, type Project } from "../api/client";

vi.mock("../api/client", () => ({
  apiClient: {
    listProjects: vi.fn(),
    createProject: vi.fn(),
    updateProject: vi.fn(),
    deleteProject: vi.fn(),
  },
}));

const PROJECTS: Project[] = [
  {
    id: "acme",
    name: "Acme",
    description: "An acme project",
    archived: false,
    created_at: "2026-06-22T00:00:00Z",
    test_types: ["ui"],
    default_environment: "dev",
    environments: [],
  },
];

function renderPage() {
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter initialEntries={["/projects"]}>
        <Routes>
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<div>project detail</div>} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe("ProjectsPage", () => {
  beforeEach(() => {
    vi.mocked(apiClient.listProjects).mockResolvedValue(PROJECTS);
  });

  it("renders a tile per project with title and description", async () => {
    renderPage();

    expect(await screen.findByText("Acme")).toBeInTheDocument();
    expect(screen.getByText("An acme project")).toBeInTheDocument();
  });

  it("navigates into the project when the tile body is clicked", async () => {
    renderPage();
    const title = await screen.findByText("Acme");

    await userEvent.click(title);

    expect(await screen.findByText("project detail")).toBeInTheDocument();
  });

  it("opens the edit dialog without navigating when the edit icon is clicked", async () => {
    renderPage();
    await screen.findByText("Acme");

    await userEvent.click(screen.getByLabelText("edit Acme"));

    expect(screen.getByText("Edit Project")).toBeInTheDocument();
    expect(screen.queryByText("project detail")).not.toBeInTheDocument();
  });

  it("opens the delete confirmation without navigating when the delete icon is clicked", async () => {
    renderPage();
    await screen.findByText("Acme");

    await userEvent.click(screen.getByLabelText("delete Acme"));

    expect(screen.getByText("Delete project")).toBeInTheDocument();
    expect(screen.queryByText("project detail")).not.toBeInTheDocument();
  });

  it("navigates into the project when the left-side open icon is clicked", async () => {
    renderPage();
    await screen.findByText("Acme");

    await userEvent.click(screen.getByLabelText("open Acme"));

    expect(await screen.findByText("project detail")).toBeInTheDocument();
  });
});
