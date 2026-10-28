import { render, screen, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { MapTabList } from "../src/components/MapTabs";
import { SectionTabs } from "../src/components/SectionTabs";
import { TipProvider } from "../src/components/Tip";
import { MAP_TABS, tabsFor } from "../src/lib/mapTabs";

const css = (file: string) => readFileSync(resolve(__dirname, "../src/styles", file), "utf8");

/** The declarations of the first rule whose selector list contains `selector` exactly. */
function rule(sheet: string, selector: string): string {
  for (const m of sheet.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const selectors = (m[1] ?? "").split(",").map((s) => s.trim());
    if (selectors.includes(selector)) return m[2] ?? "";
  }
  return "";
}

describe("map page tabs look like the Library and BeatSaver tabs", () => {
  test("the tablist uses the section tabs' pill class and each tab carries an icon", () => {
    const { container } = render(
      <MemoryRouter>
        <TipProvider delayDuration={0}>
          <SectionTabs active="library" heading="Library" headingId="h" />
        </TipProvider>
        <MapTabList available={tabsFor(true)} active="status" onSelect={() => undefined} />
      </MemoryRouter>,
    );
    const section = container.querySelector("nav.mode-switch") as HTMLElement;
    const list = screen.getByRole("tablist", { name: "Map" });
    expect(section).not.toBeNull();
    expect(list).toHaveClass("mode-switch");
    const tabs = within(list).getAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual(["Status", "Crop", "Delete"]);
    for (const t of tabs) expect(t.querySelector("svg.ic")).not.toBeNull();
    expect(MAP_TABS.map((t) => t.icon)).toEqual(["info", "scissors", "trash"]);
  });

  test("the tab buttons repeat the pill's look: muted, ink and panel when selected, blue underline", () => {
    const sheet = css("crop.css");
    const section = css("beatsaver.css");
    const selected = rule(sheet, '.mode-switch .map-tab[aria-selected="true"]');
    expect(selected).toContain("color: var(--ink)");
    expect(selected).toContain("background: var(--panel-2)");
    expect(selected).toContain("inset 0 -2px 0 var(--blue)");
    expect(rule(section, '.mode-switch a[aria-current="page"]')).toContain(
      "inset 0 -2px 0 var(--blue)",
    );
    expect(rule(sheet, ".mode-switch .map-tab")).toContain("color: var(--muted)");
    expect(rule(sheet, ".mode-switch .map-tab")).toContain("min-height: 40px");
  });
});

describe("crop chart styles", () => {
  test("the legend is centred", () => {
    const legend = rule(css("crop.css"), ".nps-legend");
    expect(legend).toContain("justify-content: center");
    expect(legend).not.toMatch(/margin:[^;]*2\.2rem/);
  });

  test("the play button is a bare green icon on a transparent background", () => {
    const play = rule(css("crop.css"), ".nps-play");
    expect(play).toContain("background: transparent");
    expect(play).toContain("color: var(--green)");
    expect(play).toContain("border: 0");
    expect(play).toContain("top: 50%");
    expect(play).toContain("translate(-50%, -50%)");
  });

  test("the playhead triangle is green", () => {
    expect(rule(css("crop.css"), ".nps-cue")).toContain("color: var(--green)");
  });

  test("the length row wraps so a phone needs no sideways scroll", () => {
    expect(rule(css("crop.css"), ".crop-bar")).toContain("flex-wrap: wrap");
    expect(rule(css("crop.css"), ".crop-actions")).toContain("flex-wrap: wrap");
  });
});
