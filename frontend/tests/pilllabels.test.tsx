import * as Tooltip from "@radix-ui/react-tooltip";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, test } from "vitest";
import { PillTabs, type PillTab } from "../src/components/PillTabs";

const TABS: PillTab[] = [
  { key: "a", path: "/a", label: "Library", icon: "library", tip: "t" },
  { key: "b", path: "/b", label: "Jobs", icon: "queue", tip: "t", badge: 3 },
];

test("every tab hides its label visually, keeps it as the name and keeps the badge", () => {
  const { container } = render(
    <MemoryRouter>
      <Tooltip.Provider>
        <PillTabs label="Section" tabs={TABS} active="a" />
      </Tooltip.Provider>
    </MemoryRouter>,
  );
  expect(container.querySelectorAll(".pill > .label-collapsible")).toHaveLength(2);
  expect(screen.getByRole("link", { name: "Library" })).toBeTruthy();
  expect(screen.getByLabelText("3 active").textContent).toBe("3");
});
