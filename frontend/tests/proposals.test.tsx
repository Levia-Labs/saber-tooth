import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";
import type { Proposal } from "../src/api/types";
import { beatRange, countOperations } from "../src/lib/timeline";
import { item, mockFetch, renderApp } from "./helpers";

function css(name: string) {
  return readFileSync(resolve(__dirname, "../src/styles", name), "utf8");
}

const note = { beat: 4, x: 1, y: 0, color: 0, cut: 1 };
function proposal(id: number, patch: Partial<Proposal> = {}): Proposal {
  return {
    id,
    rule: "flip-cut",
    difficulty: "Hard",
    severity: "error",
    summary: `Fix ${id}`,
    status: "pending",
    before: [note],
    after: [{ ...note, beat: 9, cut: 0 }],
    walls_before: [],
    walls_after: [],
    walls_context: [],
    ...patch,
  };
}

function mapApi(proposals: Proposal[]) {
  mockFetch((url) => {
    if (url.pathname === "/api/maps/id0000000001") return item(1);
    if (url.pathname.endsWith("/proposals")) return proposals;
    return {};
  });
}

describe("map page", () => {
  test("a clock icon precedes the length and BPM keeps its icon", async () => {
    mapApi([]);
    const { container } = renderApp("/maps/id0000000001");
    await screen.findByRole("heading", { name: "Song 1" });
    const items = [...container.querySelectorAll(".tempo .tempo-item")];
    expect(items).toHaveLength(2);
    expect(items[0]?.querySelector("svg")).not.toBeNull();
    expect(items[0]?.textContent).toBe("3:21");
    expect(items[1]?.querySelector("svg")).not.toBeNull();
    expect(items[1]?.textContent).toBe("128 BPM");
  });
});

describe("proposal cards", () => {
  test("collapsed by default with a one-line summary and inline buttons", async () => {
    mapApi([proposal(1), proposal(2)]);
    renderApp("/maps/id0000000001");
    const card = (await screen.findAllByText("Fix 1"))[0]?.closest("article") as HTMLElement;
    const toggle = within(card).getByRole("button", { expanded: false });
    expect(toggle).toHaveAttribute("aria-controls");
    const text = toggle.textContent ?? "";
    expect(text).toContain("flip-cut");
    expect(text).toContain("Hard");
    expect(text).toContain("2:1 - 3:2");
    expect(text).toContain("2 operations");
    expect(text).toContain("error");
    expect(within(card).getByRole("button", { name: "Approve" })).toBeVisible();
    expect(within(card).getByRole("button", { name: "Reject" })).toBeVisible();
    expect(card.querySelector(".card-body")).toHaveAttribute("hidden");
    expect(card.querySelector("canvas")).not.toBeNull();
  });

  test("Enter and Space on the summary expand and collapse it", async () => {
    mapApi([proposal(1)]);
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    const card = (await screen.findAllByText("Fix 1"))[0]?.closest("article") as HTMLElement;
    const toggle = within(card).getByRole("button", { expanded: false });
    toggle.focus();
    await user.keyboard("{Enter}");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(card.querySelector(".card-body")).not.toHaveAttribute("hidden");
    expect(document.getElementById(toggle.getAttribute("aria-controls") ?? "")).toBe(
      card.querySelector(".card-body"),
    );
    await user.keyboard(" ");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  test("Expand all and Collapse all drive every card", async () => {
    mapApi([proposal(1), proposal(2, { difficulty: "Expert" })]);
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await screen.findAllByText("Fix 1");
    await user.click(screen.getByRole("button", { name: "Expand all" }));
    expect(document.querySelectorAll(".card-toggle[aria-expanded=true]")).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "Collapse all" }));
    expect(document.querySelectorAll(".card-toggle[aria-expanded=false]")).toHaveLength(2);
  });

  test("a superseded card shows a muted chip and cannot be decided", async () => {
    mapApi([proposal(1, { status: "superseded" }), proposal(2)]);
    renderApp("/maps/id0000000001");
    const card = (await screen.findAllByText("Fix 1"))[0]?.closest("article") as HTMLElement;
    expect(card).toHaveClass("st-superseded");
    expect(within(card).getByText("Superseded")).toHaveClass("badge-muted");
    expect(within(card).getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(within(card).getByRole("button", { name: "Reject" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Approve all" })).toBeEnabled();
  });

  test("only superseded proposals leave Approve all disabled", async () => {
    mapApi([proposal(1, { status: "superseded" })]);
    renderApp("/maps/id0000000001");
    await screen.findAllByText("Fix 1");
    expect(screen.getByRole("button", { name: "Approve all" })).toBeDisabled();
  });

  test("overlapping proposals show an Overlaps chip with the ids", async () => {
    mapApi([proposal(1, { conflicts_with: [2, 5] }), proposal(2)]);
    renderApp("/maps/id0000000001");
    const card = (await screen.findAllByText("Fix 1"))[0]?.closest("article") as HTMLElement;
    expect(within(card).getByText("Overlaps #2, #5")).toBeInTheDocument();
    const other = (await screen.findAllByText("Fix 2"))[0]?.closest("article") as HTMLElement;
    expect(within(other).queryByText(/Overlaps/)).toBeNull();
  });

  test("the expanded body has a capped, scrolling height", () => {
    expect(css("page.css")).toMatch(/\.card-body\s*\{[^}]*max-height:\s*40vh[^}]*overflow:\s*auto/);
  });
});

describe("proposal summary maths", () => {
  test("bar and beat range is 1-based with four beats to a bar", () => {
    expect(beatRange([{ beat: 0 }], [])).toBe("1:1");
    expect(beatRange([{ beat: 4 }], [{ beat: 9.5 }])).toBe("2:1 - 3:2");
    expect(beatRange([], [])).toBe("no notes");
  });

  test("operations count what differs between before and after", () => {
    const a = { beat: 1, x: 0, y: 0, color: 0, cut: 1 };
    expect(countOperations([a], [a])).toBe(0);
    expect(countOperations([a], [{ ...a, cut: 2 }])).toBe(2);
    expect(countOperations([], [a])).toBe(1);
  });
});
