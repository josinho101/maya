import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider } from "@mui/material";
import theme from "../theme/theme";
import ProjectFormDialog from "./ProjectFormDialog";
import { ApiError, apiClient, type Project } from "../api/client";

vi.mock("../api/client", async () => {
  class MockApiError extends Error {
    status: number;
    detail?: string;
    constructor(status: number, detail?: string) {
      super(detail ?? `Request failed: ${status}`);
      this.status = status;
      this.detail = detail;
    }
  }
  return {
    ApiError: MockApiError,
    apiClient: {
      createProject: vi.fn(),
      updateProject: vi.fn(),
    },
  };
});

const EXISTING: Project = {
  id: "acme",
  name: "Acme",
  description: "Original description",
  archived: false,
  test_types: ["ui"],
  default_environment: "dev",
  environments: [],
};

function renderDialog(props: Partial<React.ComponentProps<typeof ProjectFormDialog>> = {}) {
  const onSaved = vi.fn();
  const onClose = vi.fn();
  render(
    <ThemeProvider theme={theme}>
      <ProjectFormDialog
        open
        mode="create"
        onClose={onClose}
        onSaved={onSaved}
        {...props}
      />
    </ThemeProvider>,
  );
  return { onSaved, onClose };
}

describe("ProjectFormDialog", () => {
  it("submits create payload with name/description/test_types and no id field", async () => {
    const created: Project = { ...EXISTING, id: "new-proj", name: "New Proj" };
    vi.mocked(apiClient.createProject).mockResolvedValue(created);
    const { onSaved } = renderDialog();

    expect(screen.queryByLabelText("Project ID")).not.toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Name"), "New Proj");
    await userEvent.type(screen.getByLabelText("Description"), "A new project");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(apiClient.createProject).toHaveBeenCalledWith({
      name: "New Proj",
      description: "A new project",
      test_types: ["ui"],
    });
    expect(onSaved).toHaveBeenCalledWith(created);
  });

  it("shows a question prompting the test type selection", () => {
    renderDialog();

    expect(screen.getByText("What kind of testing does this project need?")).toBeInTheDocument();
    expect(screen.getByLabelText("UI testing")).toBeInTheDocument();
    expect(screen.getByLabelText("API testing")).toBeInTheDocument();
  });

  it("pre-fills and submits update payload in edit mode", async () => {
    const updated: Project = { ...EXISTING, description: "Updated description" };
    vi.mocked(apiClient.updateProject).mockResolvedValue(updated);
    const { onSaved } = renderDialog({ mode: "edit", project: EXISTING });

    const description = screen.getByLabelText("Description");
    await userEvent.clear(description);
    await userEvent.type(description, "Updated description");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(apiClient.updateProject).toHaveBeenCalledWith("acme", {
      name: "Acme",
      description: "Updated description",
      test_types: ["ui"],
    });
    expect(onSaved).toHaveBeenCalledWith(updated);
  });

  it("shows a name-conflict error on a 409 instead of throwing", async () => {
    vi.mocked(apiClient.createProject).mockRejectedValue(
      new ApiError(409, "A project with this name already exists."),
    );
    renderDialog();

    await userEvent.type(screen.getByLabelText("Name"), "Acme");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("A project with this name already exists.")).toBeInTheDocument();
  });
});
