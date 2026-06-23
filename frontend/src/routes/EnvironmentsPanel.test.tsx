import { beforeEach, describe, expect, it, vi } from "vitest";
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
      listEnvironments: vi.fn(),
      addEnvironment: vi.fn(),
      updateEnvironment: vi.fn(),
      getEnvironment: vi.fn(),
      updatePackage: vi.fn(),
      deleteEnvironment: vi.fn(),
      archiveEnvironment: vi.fn(),
      downloadEnvironmentSampleJson: vi.fn(),
      parseEnvironmentJson: vi.fn(),
    },
  };
});

const PROJECT: Project = {
  id: "acme",
  name: "Acme",
  description: null,
  archived: false,
  created_at: "2026-06-22T00:00:00Z",
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
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders environments as tiles and submits the add-environment form with a tag and the default schedule preset", async () => {
    vi.mocked(apiClient.listEnvironments).mockResolvedValue([ENVIRONMENT]);
    vi.mocked(apiClient.addEnvironment).mockResolvedValue({ ...ENVIRONMENT, id: "staging" });
    renderAt("/");

    expect(await screen.findByText("Dev")).toBeInTheDocument();

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
    vi.mocked(apiClient.listEnvironments).mockResolvedValue([]);
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

  it("populates the manual form from an uploaded JSON file and applies package fields on add", async () => {
    vi.mocked(apiClient.listEnvironments).mockResolvedValue([]);
    vi.mocked(apiClient.parseEnvironmentJson).mockResolvedValue({
      tag: "prod",
      schedule: { cron: "0 0 * * *" },
      is_destructive_safe: false,
      base_url: "https://prod.acme.com",
      auth: null,
      env_vars: { KEY: "value" },
    });
    vi.mocked(apiClient.addEnvironment).mockResolvedValue({ ...ENVIRONMENT, id: "prod" });
    renderAt("/");

    await userEvent.click(screen.getByRole("button", { name: /add environment/i }));
    await userEvent.click(screen.getByRole("tab", { name: "Upload JSON" }));

    const file = new File(["{}"], "environment.json", { type: "application/json" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, file);

    expect(await screen.findByDisplayValue("prod")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(apiClient.addEnvironment).toHaveBeenCalledWith("acme", {
      tag: "prod",
      schedule: { cron: "0 0 * * *" },
      is_destructive_safe: false,
    });
    expect(apiClient.updatePackage).toHaveBeenCalledWith("acme", "prod", "ui", {
      base_url: "https://prod.acme.com",
      auth: null,
      env_vars: { KEY: "value" },
    });
  });

  it("edits an environment's schedule via the edit icon without touching its package config", async () => {
    vi.mocked(apiClient.listEnvironments).mockResolvedValue([ENVIRONMENT]);
    vi.mocked(apiClient.updateEnvironment).mockResolvedValue({
      ...ENVIRONMENT,
      schedule: { cron: "0 0 * * *" },
    });
    renderAt("/");

    await screen.findByText("Dev");
    await userEvent.click(screen.getByLabelText("edit Dev"));

    expect(screen.getByText("Edit Environment")).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Upload JSON" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByLabelText("Run schedule"));
    await userEvent.click(screen.getByRole("option", { name: "Daily at midnight" }));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(apiClient.updateEnvironment).toHaveBeenCalledWith("acme", "dev", {
      label: "Dev",
      schedule: { cron: "0 0 * * *" },
      is_destructive_safe: false,
    });
    expect(apiClient.addEnvironment).not.toHaveBeenCalled();
    expect(apiClient.updatePackage).not.toHaveBeenCalled();
  });

  it("submits the ui package form with merged fields and renders a disabled API section, with no instructions field", async () => {
    vi.mocked(apiClient.listEnvironments).mockResolvedValue([ENVIRONMENT]);
    vi.mocked(apiClient.getEnvironment).mockResolvedValue(ENVIRONMENT);
    vi.mocked(apiClient.updatePackage).mockResolvedValue(ENVIRONMENT);
    renderAt("/dev");

    const baseUrlField = await screen.findByLabelText("Base URL");
    await userEvent.type(baseUrlField, "https://staging.acme.com");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(apiClient.updatePackage).toHaveBeenCalledWith(
      "acme",
      "dev",
      "ui",
      expect.objectContaining({ base_url: "https://staging.acme.com" }),
    );
    expect(apiClient.updatePackage).not.toHaveBeenCalledWith(
      "acme",
      "dev",
      "ui",
      expect.objectContaining({ instructions: expect.anything() }),
    );

    expect(screen.queryByLabelText("Instructions")).not.toBeInTheDocument();
    expect(screen.getByText("API package configuration coming soon (F17).")).toBeInTheDocument();
  });
});
