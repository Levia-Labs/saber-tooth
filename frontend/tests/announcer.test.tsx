import { useEffect } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { AnnouncerProvider, useAnnounce } from "../src/components/Announcer";
import type { AnnounceInput } from "../src/lib/announcements";

let sendFn: (input: AnnounceInput) => void = () => undefined;

function Grab() {
  const announce = useAnnounce();
  useEffect(() => {
    sendFn = announce;
  }, [announce]);
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
