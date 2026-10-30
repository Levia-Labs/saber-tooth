import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { FACETS, inlineText, item, mockFetch, renderApp, toasts } from "./helpers";

const mapItem = item(1, { status: "error", errors: 2 });

const F = {
  rule: "r",
  difficulty: "Hard",
  beat_start: 1,
  beat_end: 1,
  severity: "error",
  message: "m",
  time_s: 1,
  proposal_id: null,
};

function api(scanStatus: "failed" | "done", findings: unknown[] = [F, { ...F, beat_start: 2 }]) {
  return mockFetch((url, init) => {
    if (init?.method === "POST") return { job: "js" };
    if (url.pathname === "/api/maps/facets") return FACETS;
    if (url.pathname === "/api/maps/id0000000001") return mapItem;
    if (url.pathname.endsWith("/proposals")) return [];
    if (url.pathname.endsWith("/findings")) return { scanned: true, findings };
    if (url.pathname === "/api/jobs/js") {
      return {
        id: "js",
        kind: "scan",
        status: scanStatus,
        error: scanStatus === "failed" ? "scanner crashed" : null,
        result: scanStatus === "done" ? { proposals: [] } : null,
      };
    }
    return { items: [mapItem], total: 1, offset: 0, limit: 40 };
  });
}

const scans = (fn: { mock: { calls: unknown[][] } }) =>
  fn.mock.calls.filter(
    ([u, i]) => String(u).endsWith("/scan") && (i as RequestInit)?.method === "POST",
  ).length;

describe("map page outcomes are toasts", () => {
  test("a failed scan is a danger toast at the bottom and Try again rescans", async () => {
    const { fn } = api("failed");
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Scan" }));
    const title = await toasts().findByText("Scan failed");
    expect((title.closest(".alert") as HTMLElement).className).toContain("alert-danger");
    expect(inlineText("Scan failed")).toBe(false);
    expect(scans(fn)).toBe(1);
    await user.click(toasts().getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(scans(fn)).toBe(2));
  });

  test("a finished scan is a success toast, not an inline alert", async () => {
    api("done");
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Scan" }));
    const title = await toasts().findByText("Scan finished");
    expect((title.closest(".alert") as HTMLElement).className).toContain("alert-success");
    expect(inlineText("Scan finished")).toBe(false);
  });

  test("the empty state stays inline on the page", async () => {
    api("done", []);
    renderApp("/maps/id0000000001");
    const empty = await screen.findByText("No issues found");
    expect(empty.closest(".toast-stack")).toBeNull();
  });
});
