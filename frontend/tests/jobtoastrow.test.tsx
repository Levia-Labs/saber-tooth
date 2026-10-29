import { act, fireEvent, render, screen } from "@testing-library/react";
import { useEffect } from "react";
import { describe, expect, test, vi } from "vitest";
import { AnnouncerProvider, useAnnounce } from "../src/components/Announcer";
import type { AnnounceInput } from "../src/lib/announcements";

let send: (input: AnnounceInput) => void = () => undefined;

function Grab() {
  const announce = useAnnounce();
  useEffect(() => {
    send = announce;
  }, [announce]);
  return null;
}

function setup(input: Partial<AnnounceInput> = {}) {
  const open = vi.fn();
  const closed = vi.fn();
  render(
    <AnnouncerProvider>
      <Grab />
    </AnnouncerProvider>,
  );
  act(() =>
    send({
      key: "Fix:m1",
      variant: "progress",
      title: "Fix Song",
      rounds: "2/6",
      onOpen: open,
      onDismiss: closed,
      ...input,
    }),
  );
  return { open, closed };
}

describe("job toast row", () => {
  test("one row: spinner, title, gold rounds, close; no action buttons", () => {
    setup();
    const row = screen.getByRole("status");
    expect(row.querySelector(".alert-spin")).not.toBeNull();
    expect(screen.getByText("Fix Song")).toBeTruthy();
    expect(screen.getByText("2/6").className).toContain("toast-rounds");
    expect(screen.queryByRole("button", { name: /cancel/i })).toBeNull();
    expect(row.querySelectorAll("button")).toHaveLength(2);
    expect(row.querySelector(".alert-actions")).toBeNull();
  });

  test("rounds are left out when unknown", () => {
    setup({ rounds: undefined });
    expect(document.querySelector(".toast-rounds")).toBeNull();
  });

  test("clicking the body opens; the X closes without opening", () => {
    const { open, closed } = setup();
    fireEvent.click(screen.getByText("Fix Song"));
    expect(open).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Fix Song")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(open).toHaveBeenCalledTimes(1);
    expect(closed).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Fix Song")).toBeNull();
  });

  test("an outcome toast is one row with its message and opens on click", () => {
    const { open } = setup({ variant: "danger", rounds: undefined, message: "boom" });
    expect(screen.getByRole("alert").querySelectorAll("button")).toHaveLength(2);
    expect(screen.getByText("boom")).toBeTruthy();
    fireEvent.click(screen.getByText("boom"));
    expect(open).toHaveBeenCalledTimes(1);
  });
});
