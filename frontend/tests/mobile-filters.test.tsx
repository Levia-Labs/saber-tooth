import { mediaFor } from "../src/lib/breakpoint";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ActionButton } from "../src/components/Buttons";
import { TextFilterBody } from "../src/components/FilterBodies";
import { TipProvider } from "../src/components/Tip";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const real = window.matchMedia;
afterEach(() => {
  window.matchMedia = real;
});

function viewport(width: number) {
  window.matchMedia = ((query: string) => {
    const max = /\(max-width:\s*([\d.]+)px\)/.exec(mediaFor(query, false));
    return { ...real(query), media: query, matches: max ? width <= Number(max[1]) : false };
  }) as typeof window.matchMedia;
}

const css = (name: string) => readFileSync(resolve(__dirname, "../src/styles", name), "utf8");

function library(rows = [item(1)]) {
  mockFetch((url) =>
    url.pathname === "/api/maps/facets"
      ? FACETS
      : { items: rows, total: rows.length, offset: 0, limit: 40 },
  );
}

async function openSheet(url = "/") {
  viewport(800);
  library();
  const view = renderApp(url);
  await screen.findByRole("link", { name: "Song 1" });
  const user = userEvent.setup();
  const trigger = screen.getByRole("button", { name: /Filters/ });
  await user.click(trigger);
  const sheet = await screen.findByRole("dialog", { name: "Filters" });
  return { ...view, user, trigger, sheet };
}

describe("fullscreen sheet", () => {
  test("is sized 100dvw x 100dvh with safe-area insets", () => {
    const sheet = /\.sheet \{[^}]*\}/.exec(css("overlays.css"))?.[0] ?? "";
    expect(sheet).toContain("100dvw");
    expect(sheet).toContain("100dvh");
    expect(sheet).toContain("safe-area-inset-top");
    expect(css("overlays.css")).toMatch(/\.sheet-foot \{[^}]*safe-area-inset-bottom/);
  });

  test("Escape closes it and focus returns to the Filters button", async () => {
    const { user, trigger, sheet } = await openSheet();
    expect(sheet.contains(document.activeElement)).toBe(true);
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(trigger).toHaveFocus();
  });

  test("focus stays inside while tabbing", async () => {
    const { user, sheet } = await openSheet();
    for (let i = 0; i < 12; i++) {
      await user.tab();
      expect(sheet.contains(document.activeElement)).toBe(true);
    }
  });
});

describe("top bar", () => {
  test("title left, then Clear all and Close icon buttons with tips", async () => {
    const { user, sheet } = await openSheet("/?status=error");
    const head = sheet.querySelector(".sheet-head") as HTMLElement;
    const buttons = within(head).getAllByRole("button");
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Clear all",
      "Close filters",
    ]);
    expect(head.firstElementChild?.textContent).toBe("Filters");
    expect(buttons.every((b) => b.textContent === "")).toBe(true);
    await user.hover(buttons[0]!);
    expect((await screen.findAllByText("Clear all filters")).length).toBeGreaterThan(0);
  });

  test("Clear all resets the filters and Close closes", async () => {
    const { user, router, sheet } = await openSheet("/?status=error");
    await user.click(within(sheet).getByRole("button", { name: "Clear all" }));
    await waitFor(() => expect(router.state.location.search).toBe(""));
    expect(within(sheet).getByRole("button", { name: "Clear all" })).toBeDisabled();
    await user.click(within(sheet).getByRole("button", { name: "Close filters" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});

describe("text inputs", () => {
  test("no visible labels; aria-label and short placeholders remain", async () => {
    const { user, sheet } = await openSheet();
    expect(within(sheet).queryByText("Title contains")).toBeNull();
    expect(within(sheet).queryByText("Name contains")).toBeNull();
    await user.click(within(sheet).getByRole("button", { name: /^Title/ }));
    await user.click(within(sheet).getByRole("button", { name: /^Author/ }));
    expect(within(sheet).getByLabelText("Title contains")).toHaveAttribute("placeholder", "Title");
    expect(within(sheet).queryByLabelText("Name contains")).toBeNull();
  });

  test("X button appears only with text, has no search icon, and clears", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const { container } = render(
      <TextFilterBody label="Title contains" placeholder="Title" q="" onChange={onChange} />,
    );
    expect(container.querySelector("svg.ic")).toBeNull();
    expect(screen.queryByRole("button", { name: "Clear" })).toBeNull();
    await user.type(screen.getByLabelText("Title contains"), "moon");
    await user.click(screen.getByRole("button", { name: "Clear" }));
    expect(onChange).toHaveBeenLastCalledWith("", true);
    expect(screen.getByLabelText("Title contains")).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Clear" })).toBeNull();
  });

  test("the desktop header popover uses the same input", async () => {
    viewport(1400);
    library();
    renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Filter Title" }));
    const input = await screen.findByLabelText("Title contains");
    expect(input).toHaveAttribute("placeholder", "Title");
    await user.type(input, "x");
    expect(screen.getByRole("button", { name: "Clear Title filter" })).toBeEnabled();
  });
});

describe("accordion groups", () => {
  test("seven groups, collapsed by default, many can be open", async () => {
    const { user, sheet } = await openSheet();
    const heads = [...sheet.querySelectorAll<HTMLButtonElement>(".acc-head")];
    expect(heads.map((h) => h.querySelector(".acc-title")?.textContent)).toEqual([
      "Title",
      "Author",
      "Levels",
      "Length",
      "BPM",
      "Env",
      "Status",
    ]);
    expect(heads.every((h) => h.getAttribute("aria-expanded") === "false")).toBe(true);
    for (const h of heads.slice(2, 4)) {
      const panel = sheet.querySelector(`#${CSS.escape(h.getAttribute("aria-controls")!)}`);
      expect(panel).toHaveAttribute("hidden");
      await user.click(h);
      expect(h).toHaveAttribute("aria-expanded", "true");
      expect(panel).not.toHaveAttribute("hidden");
    }
    expect(heads[2]).toHaveAttribute("aria-expanded", "true");
    await user.click(heads[2]!);
    expect(heads[2]).toHaveAttribute("aria-expanded", "false");
  });

  test("active groups show a count or short names", async () => {
    const { sheet } = await openSheet("/?status=error,warn&level=Easy,Normal&env=Origins&q=moon");
    const badge = (name: string) =>
      [...sheet.querySelectorAll(".acc-head")]
        .find((h) => h.querySelector(".acc-title")?.textContent === name)
        ?.querySelector(".filter-badge")?.textContent;
    expect(badge("Title")).toBe("1");
    expect(badge("Levels")).toBe("Ea, No");
    expect(badge("Status")).toBe("Er, Wa");
    expect(badge("Env")).toBe("Or");
    expect(badge("Author")).toBeUndefined();
  });
});

describe("Show button", () => {
  test("shows the live match count, is sticky, and closes the sheet", async () => {
    const { user, sheet } = await openSheet();
    const show = within(sheet).getByRole("button", { name: "Show 1" });
    expect(sheet.querySelector(".sheet-foot")).toContainElement(show);
    expect(sheet.querySelector(".sheet-body")).not.toContainElement(show);
    expect(css("overlays.css")).toMatch(/\.sheet-body \{[^}]*overflow-y: auto/);
    await user.click(show);
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});

describe("icon-only actions on mobile", () => {
  test("the label span carries the hide class and the button keeps its name", () => {
    render(
      <TipProvider>
        <ActionButton icon="scan" label="Scan Song" tip="Scan it" text />
      </TipProvider>,
    );
    const button = screen.getByRole("button", { name: "Scan Song" });
    expect(button.querySelector("span.label-collapsible")?.textContent).toBe("Scan Song");
    expect(css("overlays.css")).toMatch(/\.label-collapsible\[data-collapsed\] \{[^}]*clip/);
  });

  test("card actions no longer render short text labels", async () => {
    viewport(600);
    library([item(1, { approved: 1 })]);
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: /Review Song 1/ });
    expect(container.querySelector(".short")).toBeNull();
    expect(screen.getByRole("button", { name: /Fix Song 1/ })).toBeInTheDocument();
  });

  test("unreadable maps show only the chip on mobile; the reason stays in its name", async () => {
    viewport(600);
    const reason = "bad Info.dat ".repeat(40).trim();
    library([item(1, { status: "unreadable", parse_error: reason })]);
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(container.querySelector(".sub-unreadable")).not.toBeNull();
    expect(container.textContent).not.toContain(reason);
    expect(
      screen.getByRole("link", { name: `Open map: Unreadable: ${reason}` }),
    ).toBeInTheDocument();
    expect(css("rows.css")).toMatch(
      /@media \(max-width: 719.98px\) \{\s*\.sub-unreadable \{\s*display: none/,
    );
    expect(css("rows.css")).toMatch(/\.sub-unreadable \{[^}]*text-overflow: ellipsis/);
    expect(css("chips.css")).toMatch(/\.chip \{\s*max-width: 100%;\s*white-space: nowrap/);
  });
});
