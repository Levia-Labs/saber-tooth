import { render, screen } from "@testing-library/react";
import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { LevelChips, StatusChip } from "../src/components/Chips";
import { formatBpm, formatDuration } from "../src/lib/format";
import { contrast, LEVELS, levelsFor, textColor } from "../src/lib/levels";
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
    render(<LevelChips names={["ExpertPlus", "Easy", "Hard", "Unknown"]} />);
    const items = screen.getAllByRole("listitem").map((li) => li.textContent);
    expect(items).toEqual(["Easy", "Hard", "Expert+"]);
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
  test.each([
    [{ status: "error", errors: 3, warnings: 0 }, "3 errors"],
    [{ status: "error", errors: 1, warnings: 2 }, "1 error"],
    [{ status: "warn", errors: 0, warnings: 1 }, "1 warning"],
    [{ status: "ok", ...base }, "All good"],
    [{ status: "unscanned", ...base }, "Not scanned"],
    [{ status: "unreadable", ...base }, "Unreadable"],
    [{ status: "scanning", ...base }, "Scanning"],
    [{ status: "applying", ...base }, "Applying"],
    [{ status: "queued", ...base }, "Queued"],
  ] as const)("%j reads %s", (item, label) => {
    render(<StatusChip item={item} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  test("unknown status falls back to not scanned", () => {
    render(<StatusChip item={{ status: "weird" as never, ...base }} />);
    expect(screen.getByText("Not scanned")).toBeInTheDocument();
  });
});

describe("tooltip copy", () => {
  test("keeps the promises the buttons make", () => {
    expect(TIPS.scan).toContain("Nothing is written yet.");
    expect(TIPS.apply).toContain("The original map is never changed.");
    expect(TIPS.learn).toContain("again after adding new maps");
    expect(TIPS.generate).toContain("all five difficulties");
    expect(TIPS.approve).toBe("Accept this fix. It is written when you click Apply.");
    expect(TIPS.reject).toBe("Discard this fix.");
    expect(applyTip("Moon")).toContain("'Moon [saber-tooth]'");
  });
});
