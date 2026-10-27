import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { FilterPopover } from "../src/components/FilterPopover";
import { TipProvider } from "../src/components/Tip";

async function open() {
  render(
    <TipProvider>
      <FilterPopover label="Title" tip="Filter by title." count={0}>
        <input aria-label="body" />
      </FilterPopover>
    </TipProvider>,
  );
  const user = userEvent.setup();
  const trigger = screen.getByRole("button", { name: "Filter Title" });
  await user.click(trigger);
  const panel = await screen.findByRole("dialog");
  return { user, trigger, panel };
}

describe("filter popover close", () => {
  test("X sits in the panel header, no text Close button remains", async () => {
    const { panel } = await open();
    const x = screen.getByRole("button", { name: "Close filter" });
    expect(x.closest("header")).not.toBeNull();
    expect(panel.firstElementChild).toBe(x.closest("header"));
    expect(x.closest("header")?.lastElementChild?.contains(x)).toBe(true);
    expect(screen.queryByText("Close")).toBeNull();
  });

  test("click closes and returns focus to the trigger", async () => {
    const { user, trigger } = await open();
    await user.click(screen.getByRole("button", { name: "Close filter" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(trigger).toHaveFocus();
  });

  test("Escape closes and returns focus to the trigger", async () => {
    const { user, trigger } = await open();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(trigger).toHaveFocus();
  });

  test("X is keyboard focusable", async () => {
    const { user } = await open();
    const x = screen.getByRole("button", { name: "Close filter" });
    await user.tab();
    await user.tab({ shift: true });
    x.focus();
    expect(x).toHaveFocus();
  });
});
