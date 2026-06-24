import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import theme from "../theme/theme";
import RunReport from "./RunReport";
import { apiClient, type RunSummary } from "../api/client";

vi.mock("../api/client", async () => ({
  apiClient: {
    getRun: vi.fn(),
  },
}));

const SUMMARY: RunSummary = {
  run_id: "run_20260624T000000Z_abc123",
  environment_id: "dev",
  trigger: {},
  decision: {},
  total_job_time_ms: 350,
  results: [
    { test_case_id: "tc_one", status: "pass", healed_pass: false, execution_time_ms: 200, healing_event_refs: [], screenshot_refs: [], mapping_refs: [] },
    { test_case_id: "tc_two", status: "fail", healed_pass: false, execution_time_ms: 150, healing_event_refs: [], screenshot_refs: ["tc_two_0.png"], mapping_refs: [] },
  ],
  summary: { pass: 1, fail: 1 },
};

function renderAt(path: string) {
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/:runId" element={<RunReport />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe("RunReport", () => {
  it("renders pass/fail rows and the total job time", async () => {
    vi.mocked(apiClient.getRun).mockResolvedValue(SUMMARY);
    renderAt(`/${SUMMARY.run_id}`);

    expect(await screen.findByText("tc_one")).toBeInTheDocument();
    expect(screen.getByText("tc_two")).toBeInTheDocument();
    expect(screen.getByText("pass")).toBeInTheDocument();
    expect(screen.getByText("fail")).toBeInTheDocument();
    expect(screen.getByText(/Total job time: 350 ms/)).toBeInTheDocument();
    expect(apiClient.getRun).toHaveBeenCalledWith(SUMMARY.run_id);
  });
});
