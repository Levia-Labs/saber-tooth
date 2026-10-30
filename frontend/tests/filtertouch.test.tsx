import * as Tooltip from "@radix-ui/react-tooltip";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { FilterPopover } from "../src/components/FilterPopover";

const real = window.matchMedia;
afterEach(() => {
  window.matchMedia = real;
});

test("on a touch screen (hover: none) tapping a filter button opens its filter, not the tip", async () => {
  window.matchMedia = ((query: string) => ({
    matches: query.includes("hover: none"),
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  })) as unknown as typeof window.matchMedia;
  const pick = vi.fn();
  render(
    <Tooltip.Provider>
      <FilterPopover label="Status" tip="Filter by status" count={0}>
        <button type="button" onClick={pick}>
          Ranked
        </button>
      </FilterPopover>
    </Tooltip.Provider>,
  );
  await userEvent.click(screen.getByRole("button", { name: "Filter Status" }));
  expect(await screen.findByRole("dialog", { name: "Status filter" })).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: "Ranked" }));
  expect(pick).toHaveBeenCalledTimes(1);
});
