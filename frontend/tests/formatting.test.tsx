import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fc from "fast-check";
import { TipProvider } from "../src/components/Tip";
import { describe, expect, test } from "vitest";
import { LevelChips, StatusChip } from "../src/components/Chips";
import { formatBpm, formatDuration } from "../src/lib/format";
import {
  contrast,
  LEVELS,
  levelSlots,
  levelsFor,
  ringText,
  SURFACE,
  textColor,
} from "../src/lib/levels";
import { STATUS_META, STATUS_ORDER } from "../src/lib/status";
import { applyTip, TIPS } from "../src/lib/tips";

describe("formatters", () => {
  test("duration is m:ss", () => {
    expect(formatDuration(0)).toBe("0:00");
    expect(formatDuration(65)).toBe("1:05");
    expect(formatDuration(201.4)).toBe("3:21");
    expect(formatDuration(3600)).toBe("60:00");
  });

  test("unknown duration and bpm show a dash", () => {
    expect(formatDuration(null)).toBe("–");
    expect(formatBpm(null)).toBe("–");
    expect(formatBpm(Number.NaN)).toBe("–");
  });

  test("bpm is rounded with a unit", () => {
    expect(formatBpm(128)).toBe("128 BPM");
    expect(formatBpm(127.6)).toBe("128 BPM");
  });

  test("property: duration always matches m:ss", () => {
    fc.assert(
      fc.property(fc.double({ min: 0, max: 100000, noNaN: true }), (s) => {
        expect(formatDuration(s)).toMatch(/^\d+:[0-5]\d$/);
      }),
    );
  });
});

describe("level chips", () => {
  const text = (el: Element) => el.textContent;

  test("render as text separated by ' | ' in game order whatever the input order", () => {
    render(
      <TipProvider>
        <LevelChips names={["ExpertPlus", "Easy", "Hard", "Unknown"]} />
      </TipProvider>,
    );
    expect(text(screen.getByRole("group", { name: "Difficulties" }))).toBe(
      "Ea | No | Ha | Ex | Ex+",
    );
  });

  test("levels are abbreviated with the full name in the aria-label", () => {
    render(
      <TipProvider>
        <LevelChips names={["Easy", "Normal", "Hard", "Expert", "ExpertPlus"]} />
      </TipProvider>,
    );
    for (const name of ["Easy", "Normal", "Hard", "Expert", "Expert+"]) {
      expect(screen.getByRole("img", { name })).toBeInTheDocument();
    }
  });

  test("present levels carry their AA colour, no border, and the Tip carries the NPS", async () => {
    render(
      <TipProvider delayDuration={0}>
        <LevelChips names={["Expert"]} nps={{ Expert: 6.25 }} />
      </TipProvider>,
    );
    const chip = screen.getByRole("img", { name: "Expert, 6.3 NPS" });
    expect(chip.style.color).not.toBe("");
    expect(chip.style.borderColor).toBe("");
    expect(chip.style.background).toBe("");
    await userEvent.hover(chip);
    expect((await screen.findAllByText("Expert, 6.3 NPS")).length).toBeGreaterThan(0);
  });

  test("outline text colour reaches AA contrast on the dark surface", () => {
    for (const l of LEVELS) expect(contrast(ringText(l.bg), SURFACE)).toBeGreaterThanOrEqual(4.5);
  });

  test("missing difficulties are muted in their slot with a Missing Tip", async () => {
    expect(levelsFor(["Normal"]).map((l) => l.label)).toEqual(["Normal"]);
    expect(levelSlots(["Normal"]).map((s) => s.present)).toEqual([
      false,
      true,
      false,
      false,
      false,
    ]);
    render(
      <TipProvider delayDuration={0}>
        <LevelChips names={["Normal"]} />
      </TipProvider>,
    );
    const parts = Array.from(document.querySelectorAll(".level"));
    expect(parts.map((p) => p.classList.contains("missing"))).toEqual([
      true,
      false,
      true,
      true,
      true,
    ]);
    expect((parts[0] as HTMLElement).style.color).toBe("");
    expect(document.querySelectorAll(".level-sep")).toHaveLength(4);
    const gone = screen.getByRole("img", { name: "Missing: Expert+" });
    await userEvent.hover(gone);
    expect((await screen.findAllByText("Missing: Expert+")).length).toBeGreaterThan(0);
  });

  test("no difficulties at all still shows five muted slots", () => {
    render(
      <TipProvider>
        <LevelChips names={[]} />
      </TipProvider>,
    );
    expect(document.querySelectorAll(".level.missing")).toHaveLength(5);
  });

  test("beatsaver colours are used", () => {
    const colours = Object.fromEntries(LEVELS.map((l) => [l.label, l.bg]));
    expect(colours).toEqual({
      Easy: "#3CB371",
      Normal: "#59B0F4",
      Hard: "#FF6347",
      Expert: "#BF2A42",
      "Expert+": "#8F48DB",
    });
  });

  test("text colour reaches AA contrast on every level", () => {
    for (const l of LEVELS) expect(contrast(l.bg, textColor(l.bg))).toBeGreaterThanOrEqual(4.5);
  });
});

describe("status chip", () => {
  const base = { errors: 0, warnings: 0 };
  const chip = (item: Parameters<typeof StatusChip>[0]["item"]) =>
    render(
      <TipProvider>
        <StatusChip item={item} />
      </TipProvider>,
    );
  test.each([
    [{ status: "error", errors: 3, warnings: 0 }, "3 errors", "3"],
    [{ status: "error", errors: 1, warnings: 2 }, "1 error", "1"],
    [{ status: "warn", errors: 0, warnings: 1 }, "1 warning", "1"],
    [{ status: "ok", ...base }, "All good", ""],
    [{ status: "unscanned", ...base }, "Not scanned", ""],
    [{ status: "incomplete", ...base }, "Not scanned, missing levels", ""],
    [{ status: "unreadable", ...base }, "Unreadable", ""],
    [{ status: "unreadable", ...base, parse_error: "bad json" }, "Unreadable: bad json", ""],
    [{ status: "scanning", ...base }, "Scanning", ""],
    [{ status: "applying", ...base }, "Applying", ""],
    [{ status: "queued", ...base }, "Queued", ""],
  ] as const)("%j is labelled %s and shows %j", (item, label, visible) => {
    const { container } = chip(item);
    expect(screen.getByRole("img", { name: label })).toBeInTheDocument();
    expect(container.textContent).toBe(visible);
  });

  test("incomplete chip uses the unscanned icon in the warning colour", () => {
    chip({ status: "incomplete", ...base });
    const el = screen.getByRole("img", { name: "Not scanned, missing levels" });
    expect(el).toHaveClass("chip-incomplete");
    expect(STATUS_META.incomplete.icon).toBe(STATUS_META.unscanned.icon);
    expect(STATUS_ORDER.indexOf("incomplete")).toBe(STATUS_ORDER.indexOf("unscanned") - 1);
    const css = readFileSync(resolve(__dirname, "../src/styles/chips.css"), "utf8");
    expect(css).toMatch(/\.chip-incomplete\s*\{[^}]*--tone:\s*var\(--amber\)/);
  });

  test("unknown status falls back to not scanned", () => {
    const { container } = chip({ status: "weird" as never, ...base });
    expect(screen.getByRole("img", { name: "Not scanned" })).toBeInTheDocument();
    expect(container.textContent).toBe("");
  });

  test("hovering a chip shows the full meaning", async () => {
    chip({ status: "error", errors: 3, warnings: 0 });
    await userEvent.hover(screen.getByRole("img", { name: "3 errors" }));
    expect((await screen.findAllByText("3 errors")).length).toBeGreaterThan(0);
  });
});

describe("tooltip copy", () => {
  test("keeps the promises the buttons make", () => {
    expect(TIPS.scan).toContain("Nothing is written yet.");
    expect(TIPS.apply).toContain("The original map is never changed.");
    expect(TIPS.learn).toContain("Optional: Saber Tooth already lights maps with its bundled set.");
    expect(TIPS.generate).toContain("all five difficulties");
    expect(TIPS.approve).toBe("Accept this fix. It is written when you click Apply.");
    expect(TIPS.reject).toBe("Discard this fix.");
    expect(TIPS.resetColumns).toBe("Reset column widths to their defaults.");
    expect(applyTip("Moon")).toContain("'Moon [saber-tooth]'");
  });
});
