import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { ApiError } from "../src/api/client";
import type { Job, JobKind } from "../src/api/types";
import { Alert, SpecAlert } from "../src/components/Alert";
import { JobOutcome } from "../src/components/JobOutcome";
import { errorToAlert, toAlert } from "../src/lib/alerts";

const job = (kind: JobKind, patch: Partial<Job> = {}): Job => ({
  id: "j1",
  kind,
  status: "done",
  error: null,
  result: null,
  ...patch,
});

describe("toAlert", () => {
  test("nothing to report returns null", () => {
    expect(toAlert(null, null)).toBeNull();
  });

  test.each([
    ["scan", { proposals: 12 }, "Scan finished", "12 fixes proposed."],
    ["scan", { proposals: [1] }, "Scan finished", "1 fix proposed."],
    ["scan", {}, "Scan finished", "Review the proposed fixes below."],
    ["apply", { folder: "C:/maps/a" }, "Applied", "Written to C:/maps/a."],
    ["apply", {}, "Applied", "The approved fixes were applied."],
    ["generate", { map_id: 3 }, "Map generated", "Review the proposed map below."],
    ["learn", {}, "Lightshows learned", "The new lightshows are ready to use."],
  ] as const)("%s done -> success", (kind, result, title, message) => {
    const spec = toAlert(job(kind, { result }));
    expect(spec).toMatchObject({ variant: "success", title, message });
  });

  test.each([
    ["scan", "Scan failed"],
    ["apply", "Apply failed"],
    ["generate", "Generation failed"],
    ["learn", "Learning failed"],
  ] as const)("%s failed -> danger with raw text in details", (kind, title) => {
    const spec = toAlert(job(kind, { status: "failed", error: "boom" }), "boom");
    expect(spec).toMatchObject({ variant: "danger", title, details: ["boom"] });
    expect(spec?.title).not.toMatch(/:/);
  });

  test("a failed job without an error string still reports", () => {
    expect(toAlert(job("apply", { status: "failed" }))).toMatchObject({ variant: "danger" });
  });

  test("conflict lists ids and offers review", () => {
    const spec = toAlert(
      job("apply", { status: "failed", result: { conflict: [4, 7] } }),
      "conflict",
    );
    expect(spec?.message).toBe(
      "Two approved fixes change the same notes. Review the highlighted fixes and apply again.",
    );
    expect(spec?.details?.[0]).toContain("4, 7");
    expect(spec?.action?.kind).toBe("review");
  });

  test("database lock is rewritten in plain words", () => {
    const spec = toAlert(null, "database is locked");
    expect(spec?.message).toContain("busy");
    expect(spec?.details).toEqual(["database is locked"]);
  });

  test("polling timeout is a warning, cancel is info", () => {
    expect(toAlert(null, "timed out after 30 minutes")).toMatchObject({ variant: "warning" });
    expect(toAlert(null, "cancelled")).toMatchObject({ variant: "info" });
  });

  test("needs_review ids give a warning with a Review action, tolerating other fields", () => {
    const spec = toAlert(
      job("apply", {
        result: { folder: "f", applied: [1], superseded: [2], needs_review: [5, 6], extra: {} },
      }),
    );
    expect(spec).toMatchObject({
      variant: "warning",
      title: "2 fixes need another look",
      action: { kind: "review", label: "Review" },
    });
    expect(spec?.details).toEqual(["Fixes to review: 5, 6"]);
  });
});

describe("errorToAlert", () => {
  test("network failure", () => {
    const spec = errorToAlert(new TypeError("Failed to fetch"), "Could not load the map");
    expect(spec).toMatchObject({ variant: "danger", title: "Could not load the map" });
    expect(spec.message).toContain("could not be reached");
  });

  test("429 is a warning", () => {
    expect(errorToAlert(new ApiError("slow down", 429), "x").variant).toBe("warning");
  });

  test("404 has no retry; 500 does", () => {
    expect(errorToAlert(new ApiError("nope", 404), "x").action).toBeUndefined();
    expect(errorToAlert(new ApiError("HTTP 500", 500), "x").action?.kind).toBe("retry");
  });

  test("non-error values are tolerated", () => {
    expect(errorToAlert(undefined, "x").details).toEqual(["unknown error"]);
  });
});

describe("Alert", () => {
  test.each([
    ["danger", "alert"],
    ["warning", "alert"],
    ["info", "status"],
    ["success", "status"],
  ] as const)("%s has role %s", (variant, role) => {
    render(<Alert variant={variant} title="T" message="M" />);
    const el = screen.getByRole(role);
    expect(el).toHaveClass(`alert-${variant}`);
    expect(el).toHaveAttribute("aria-live", role === "alert" ? "assertive" : "polite");
  });

  test("details fold away, actions and dismiss work", async () => {
    const dismiss = vi.fn();
    const act = vi.fn();
    render(
      <Alert
        variant="danger"
        title="Apply failed"
        message="m"
        details={["raw text"]}
        actions={<button onClick={act}>Retry</button>}
        onDismiss={dismiss}
      />,
    );
    const summary = screen.getByText("Details");
    expect(summary.closest("details")).not.toHaveAttribute("open");
    await userEvent.click(summary);
    expect(summary.closest("details")).toHaveAttribute("open");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(act).toHaveBeenCalled();
    expect(dismiss).toHaveBeenCalled();
  });

  test("SpecAlert shows the action only with a handler", async () => {
    const spec = errorToAlert(new TypeError("Failed to fetch"), "t");
    const { rerender } = render(<SpecAlert spec={spec} />);
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
    const retry = vi.fn();
    rerender(<SpecAlert spec={spec} onRetry={retry} />);
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalled();
  });
});

describe("JobOutcome", () => {
  test("apply failure renders a danger alert, not Apply: failed text", () => {
    render(<JobOutcome job={null} error="database is locked" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Apply failed");
    expect(screen.queryByText(/Apply: failed/)).toBeNull();
  });

  test("renders nothing without job or error", () => {
    const { container } = render(<JobOutcome job={null} error={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
