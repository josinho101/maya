import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import theme from "../theme/theme";
import EnvironmentsPanel from "./EnvironmentsPanel";
import { ApiError, apiClient, type Environment, type Project } from "../api/client";

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
      addEnvironment: vi.fn(),
      getEnvironment: vi.fn(),
      updatePackage: vi.fn(),
      deleteEnvironment: vi.fn(),
    },
  };
});

const PROJECT: Project = {
  id: "acme",
  name: "Acme",
  description: null,
  archived: false,
  test_types: ["ui"],
  default_environment: "dev",
  environments: ["dev"],
};

const ENVIRONMENT: Environment = {
  id: "dev",
  label: "Dev",
  archived: false,
  schedule: null,
  is_destructive_safe: false,
  packages: {},
};

function renderAt(path: string) {
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter initialEntries={[path]}>
        <EnvironmentsPanel project={PROJECT} />
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe("EnvironmentsPanel", () => {
  it("submits the add-environment form with a tag and the default schedule preset, with no id field", async () => {
    vi.mocked(apiClient.addEnvironment).mockResolvedValue({ ...ENVIRONMENT, id: "staging" });
    renderAt("/");

    await userEvent.click(screen.getByRole("button", { name: /add environment/i }));

    expect(screen.queryByLabelText("Environment ID")).not.toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Tag"), "Staging");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(apiClient.addEnvironment).toHaveBeenCalledWith("acme", {
      tag: "Staging",
      schedule: { cron: "0 */6 * * *" },
      is_destructive_safe: false,
    });
  });

  it("shows a tag-conflict error on a 409 instead of throwing", async () => {
    vi.mocked(apiClient.addEnvironment).mockRejectedValue(
      new ApiError(409, "An environment with this tag already exists."),
    );
    renderAt("/");

    await userEvent.click(screen.getByRole("button", { name: /add environment/i }));
    await userEvent.type(screen.getByLabelText("Tag"), "dev");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(
      await screen.findByText("An environment with this tag already exists."),
    ).toBeInTheDocument();
  });

  it("submits the ui package form with merged fields and renders a disabled API section", async () => {
    vi.mocked(apiClient.getEnvironment).mockResolvedValue(ENVIRONMENT);
    vi.mocked(apiClient.updatePackage).mockResolvedValue(ENVIRONMENT);
    renderAt("/dev");

    const baseUrlField = await screen.findByLabelText("Base URL");
    await userEvent.type(baseUrlField, "https://staging.acme.com");
    await userEvent.click(screen.getByRole("button", { name: "Save UI Package" }));

    expect(apiClient.updatePackage).toHaveBeenCalledWith(
      "acme",
      "dev",
      "ui",
      expect.objectContaining({ base_url: "https://staging.acme.com" }),
    );

    expect(screen.getByText("API package configuration coming soon (F17).")).toBeInTheDocument();
  });
});
