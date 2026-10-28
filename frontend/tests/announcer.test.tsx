import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { useEffect } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { AnnouncerProvider, useAnnounce, useWithdraw } from "../src/components/Announcer";
import type { AnnounceInput } from "../src/lib/announcements";

let sendFn: (input: AnnounceInput) => void = () => undefined;
let withdrawFn: (key: string) => void = () => undefined;

function Grab() {
  const announce = useAnnounce();
  const withdraw = useWithdraw();
  useEffect(() => {
    sendFn = announce;
    withdrawFn = withdraw;
  }, [announce, withdraw]);
  return null;
}

const show = (input: AnnounceInput) => act(() => sendFn(input));

beforeEach(() => {
  vi.useFakeTimers();
  render(
    <AnnouncerProvider>
      <Grab />
    </AnnouncerProvider>,
  );
});
afterEach(() => vi.useRealTimers());

describe("Announcer banners", () => {
  test("progress shows a spinner and no dismiss, then success replaces it and fades", () => {
    show({ variant: "progress", title: "Fix Acid Rain", message: "Running" });
    const banner = screen.getByRole("status");
    expect(banner.querySelector(".alert-spin")).not.toBeNull();
    expect(screen.queryByRole("button", { name: "Dismiss" })).toBeNull();

    show({ variant: "success", title: "Fix Acid Rain", message: "Done" });
    expect(screen.getAllByRole("status")).toHaveLength(1);
    expect(screen.getByText("Done")).toBeTruthy();
    expect(document.querySelector(".alert-spin")).toBeNull();

    act(() => vi.advanceTimersByTime(5000));
    expect(screen.queryByText("Done")).toBeNull();
  });

  test("danger is an assertive alert that stays until dismissed", () => {
    show({ variant: "danger", title: "Fix Acid Rain", message: "boom" });
    act(() => vi.advanceTimersByTime(60_000));
    expect(screen.getByRole("alert").getAttribute("aria-live")).toBe("assertive");
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("shows at most four banners", () => {
    for (let i = 0; i < 6; i++) show({ variant: "warning", title: `job ${i}` });
    expect(screen.getAllByRole("alert")).toHaveLength(4);
    expect(screen.queryByText("job 1")).toBeNull();
    expect(screen.getByText("job 5")).toBeTruthy();
  });
});

const css = (name: string) => readFileSync(resolve(__dirname, "../src/styles", name), "utf8");

describe("Announcer toasts", () => {
  test("toasts render in a bottom container that is fixed to the bottom", () => {
    show({ variant: "progress", title: "Fix Acid Rain" });
    const stack = document.querySelector(".toast-stack") as HTMLElement;
    expect(stack.querySelector(".alert")).not.toBeNull();
    expect(document.querySelector(".banner-stack")).toBeNull();
    const rule = css("alerts.css").match(/\.toast-stack \{([^}]*)\}/)?.[1] ?? "";
    expect(rule).toMatch(/position:\s*fixed/);
    expect(rule).toMatch(/bottom:/);
    expect(rule).toMatch(/safe-area-inset-bottom/);
  });

  test("the progress toast icon has the spinning class and the CSS animates it", () => {
    show({ variant: "progress", title: "Fix Acid Rain" });
    const icon = document.querySelector(".toast-stack .alert svg") as SVGElement;
    expect(icon.getAttribute("class")).toContain("alert-spin");
    const sheet = css("alerts.css");
    expect(sheet).toMatch(/@keyframes alert-spin\s*\{[^}]*\{[^}]*rotate\(360deg\)/);
    const media = sheet.match(
      /@media \(prefers-reduced-motion: no-preference\) \{[\s\S]*?\.alert-spin \{([^}]*)\}/,
    );
    expect(media?.[1]).toMatch(/animation:\s*alert-spin/);
    // The spinner is the only sign a job is alive, so it keeps turning (slower) when the
    // system asks for reduced motion; Windows "Animation effects: off" sets that preference.
    const reduced = sheet.match(
      /@media \(prefers-reduced-motion: reduce\) \{[\s\S]*?\.alert-spin \{([^}]*)\}/,
    );
    expect(reduced?.[1]).toMatch(/animation:\s*alert-spin\s+[2-9]/);
  });
});

describe("Announcer actions", () => {
  test("action buttons run their handler, close the toast and a sticky info toast does not fade", () => {
    const run = vi.fn();
    show({
      variant: "info",
      title: "Pick one",
      sticky: true,
      actions: [{ label: "Go", onClick: run }],
    });
    act(() => vi.advanceTimersByTime(20_000));
    expect(screen.getByText("Pick one")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(run).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Pick one")).toBeNull();
  });

  test("an info toast without sticky still fades", () => {
    show({ variant: "info", title: "Brief" });
    act(() => vi.advanceTimersByTime(6000));
    expect(screen.queryByText("Brief")).toBeNull();
  });
});

describe("Announcer withdraw and close hook", () => {
  test("the close button runs onDismiss", () => {
    const closed = vi.fn();
    show({ variant: "info", title: "Closable", sticky: true, onDismiss: closed });
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(closed).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Closable")).toBeNull();
  });

  test("withdraw removes a toast by key", () => {
    show({ key: "k", variant: "warning", title: "Stays" });
    act(() => withdrawFn("k"));
    expect(screen.queryByText("Stays")).toBeNull();
  });
});
