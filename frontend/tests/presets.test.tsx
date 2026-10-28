import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { DEFAULT_BS_STATE, presetFilters } from "../src/lib/bsfilters";
import { describePreset } from "../src/lib/presetdescribe";
import { bsApi } from "./bshelpers";
import { renderApp } from "./helpers";

const SEEDED_FILTERS = {
  diffs: "Easy,Normal,Hard",
  diffs_mode: "all",
  min_rating: "0.95",
  nps_min: "1",
  nps_max: "2",
  nps_scope: "any",
  tags: "electronic,dubstep,rock,metal,punk,j-rock,techno,house,trance,drum-and-bass",
  order: "Rating",
  ascending: "false",
};

describe("describePreset", () => {
  test("describes the seeded preset in plain words", () => {
    expect(describePreset(SEEDED_FILTERS)).toBe(
      "Shows maps with Easy, Normal and Hard, rated 95% or higher, at least one difficulty at 1-2 notes per second, tagged electronic, dubstep, rock, metal, punk, j-rock, techno, house, trance or drum-and-bass, best rated first.",
    );
  });

  test("empty filters show everything, newest first", () => {
    expect(describePreset({})).toBe("Shows maps newest first.");
    expect(describePreset(presetFilters(DEFAULT_BS_STATE))).toBe("Shows maps newest first.");
  });

  test("covers search, any-mode levels, ranked, bounds and ascending order", () => {
    expect(
      describePreset({
        q: "daft",
        diffs: "Expert,ExpertPlus",
        diffs_mode: "any",
        nps_min: "5",
        nps_scope: "all",
        ranked: "true",
        order: "Latest",
        ascending: "true",
        bpm_max: "140",
      }),
    ).toBe(
      'Shows maps matching "daft", with Expert or Expert+, every difficulty at 5 or more notes per second, at up to 140 BPM, ranked, oldest first.',
    );
  });

  test("never throws on junk values", () => {
    expect(describePreset({ min_rating: "x", order: "zzz", diffs: "Nope" })).toBe(
      "Shows maps newest first.",
    );
  });
});

describe("presets bar", () => {
  test("label, centred icon chip, Tip text, active state and clearing", async () => {
    bsApi();
    const { router } = renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const group = await screen.findByRole("group", { name: "Saved filters" });
    // The bar shows only chips and Save: no "Saved searches" label, no load-error text.
    expect(within(group).queryByText("Saved searches")).toBeNull();
    expect(within(group).queryByText(/Could not load saved filters/)).toBeNull();
    const chip = await within(group).findByRole("button", { name: "Easy-to-Hard gems" });
    expect(chip.querySelector("svg")).not.toBeNull();
    expect(chip.querySelector(".ic")).not.toBeNull();
    const save = within(group).getByRole("button", { name: "Save filters" });
    expect(save.querySelector("svg")).not.toBeNull();
    await userEvent.hover(chip);
    expect(
      (await screen.findAllByText(/^Shows maps with Easy, Normal and Hard.*Click to apply\.$/))
        .length,
    ).toBeGreaterThan(0);
    await userEvent.click(chip);
    await waitFor(() => expect(chip).toHaveAttribute("aria-pressed", "true"));
    await userEvent.click(chip);
    await waitFor(() => expect(chip).toHaveAttribute("aria-pressed", "false"));
    expect(router.state.location.search).toBe("");
  });
});
