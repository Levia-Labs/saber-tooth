import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { item, mockFetch, renderApp } from "./helpers";

const FINDING = {
  rule: "flip-cut",
  difficulty: "Hard",
  beat_start: 8,
  beat_end: 8,
  severity: "error",
  message: "hand flips between swings",
  time_s: 3.75,
  proposal_id: null,
};

function api(map: ReturnType<typeof item>, findings: unknown) {
  return mockFetch((url, init) => {
    if (init?.method === "POST") return {};
    if (url.pathname === `/api/maps/${map.id}`) return map;
    if (url.pathname.endsWith("/findings")) return findings;
    if (url.pathname.endsWith("/proposals")) return [];
    return {};
  });
}

describe("Status tab findings", () => {
  test("a copy with one error and no proposal lists the error", async () => {
    api(item(1, { status: "error", errors: 1, scanned_at: "2026-01-01" }), {
      scanned: true,
      findings: [FINDING],
    });
    renderApp("/maps/id0000000001");
    expect(await screen.findByText("hand flips between swings")).toBeInTheDocument();
    expect(screen.getByText("flip-cut (1)")).toBeInTheDocument();
    expect(screen.getByText(/No automatic fix/)).toBeInTheDocument();
    expect(screen.queryByText("No fixes yet")).toBeNull();
  });

  test("a scanned clean map says No issues found", async () => {
    api(item(1, { status: "ok", scanned_at: "2026-01-01" }), { scanned: true, findings: [] });
    renderApp("/maps/id0000000001");
    expect(await screen.findByText("No issues found")).toBeInTheDocument();
  });

  test("an unscanned map says Not scanned yet and the page has one Scan button", async () => {
    const { fn } = api(item(1), { scanned: false, findings: [] });
    renderApp("/maps/id0000000001");
    expect(await screen.findByText("Not scanned yet")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Scan" }));
    await waitFor(() =>
      expect(
        fn.mock.calls.some(([u, i]) => String(u).endsWith("/scan") && i?.method === "POST"),
      ).toBe(true),
    );
  });
});
