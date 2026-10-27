import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fc from "fast-check";
import { TipProvider } from "../src/components/Tip";
import { describe, expect, test } from "vitest";
import { LevelChips, StatusChip } from "../src/components/Chips";
import { formatBpm, formatDuration } from "../src/lib/format";
import { contrast, LEVELS, levelsFor, ringText, SURFACE, textColor } from "../src/lib/levels";
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
  test("render in game order whatever the input order", () => {
    render(
      <TipProvider>
        <LevelChips names={["ExpertPlus", "Easy", "Hard", "Unknown"]} />
      </TipProvider>,
    );
    const items = screen.getAllByRole("listitem").map((li) => li.textContent);
    expect(items).toEqual(["Ea", "Ha", "Ex+"]);
  });

  test("chips are abbreviated with the full name in the aria-label", () => {
    render(
      <TipProvider>
        <LevelChips names={["Easy", "Normal", "Hard", "Expert", "ExpertPlus"]} />
      </TipProvider>,
    );
    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Ea",
      "No",
      "Ha",
      "Ex",
      "Ex+",
    ]);
    for (const name of ["Easy", "Normal", "Hard", "Expert", "Expert+"]) {
      expect(screen.getByRole("img", { name })).toBeInTheDocument();
    }
  });

  test("chips are outlined in the level colour and the Tip carries the NPS", async () => {
    render(
      <TipProvider delayDuration={0}>
        <LevelChips names={["Expert"]} nps={{ Expert: 6.25 }} />
      </TipProvider>,
    );
    const li = screen.getByRole("listitem");
    expect(li.style.borderColor).toBe("rgb(191, 42, 66)");
    expect(li.style.background).toBe("");
    const chip = screen.getByRole("img", { name: "Expert, 6.3 NPS" });
    await userEvent.hover(chip);
    expect((await screen.findAllByText("Expert, 6.3 NPS")).length).toBeGreaterThan(0);
  });

  test("outline text colour reaches AA contrast on the dark surface", () => {
    for (const l of LEVELS) expect(contrast(ringText(l.bg), SURFACE)).toBeGreaterThanOrEqual(4.5);
  });

  test("missing difficulties are not shown", () => {
    expect(levelsFor(["Normal"]).map((l) => l.label)).toEqual(["Normal"]);
    const { container } = render(<LevelChips names={[]} />);
    expect(container).toBeEmptyDOMElement();
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
    expect(TIPS.learn).toContain("Optional: saber-tooth already lights maps with its bundled set.");
    expect(TIPS.generate).toContain("all five difficulties");
    expect(TIPS.approve).toBe("Accept this fix. It is written when you click Apply.");
    expect(TIPS.reject).toBe("Discard this fix.");
    expect(TIPS.resetColumns).toBe("Reset column widths to their defaults.");
    expect(applyTip("Moon")).toContain("'Moon [saber-tooth]'");
  });
});
