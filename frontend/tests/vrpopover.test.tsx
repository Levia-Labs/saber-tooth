import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as Tooltip from "@radix-ui/react-tooltip";
import { afterEach, expect, test, vi } from "vitest";
import { FilterPopover } from "../src/components/FilterPopover";

afterEach(() => {
  delete document.documentElement.dataset.ui;
});

test("in VR the popover portals to the body, under the scaled root, and its options click", async () => {
  document.documentElement.dataset.ui = "vr";
  const pick = vi.fn();
  render(
    <Tooltip.Provider>
      <FilterPopover label="Status" tip="Filter" count={0}>
        <button type="button" onClick={pick}>
          Ranked
        </button>
      </FilterPopover>
    </Tooltip.Provider>,
  );
  await userEvent.click(screen.getByRole("button", { name: "Filter Status" }));
  const content = await screen.findByRole("dialog", { name: "Status filter" });
  expect(content.className).toContain("popover");
  expect(document.body.contains(content)).toBe(true);
  expect(content.closest("[data-ui]") ?? document.documentElement).toBe(document.documentElement);
  expect(getComputedStyle(content).pointerEvents).not.toBe("none");
  await userEvent.click(screen.getByRole("button", { name: "Ranked" }));
  expect(pick).toHaveBeenCalledTimes(1);
});
