import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { parseBsState } from "../src/lib/bsfilters";
import { parsePlState } from "../src/lib/plfilters";
import { parseState } from "../src/lib/urlstate";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

describe("old URLs with decimals read back as whole numbers", () => {
  const query = "?duration_min=127.89&duration_max=200.2&bpm_min=120.7&bpm_max=140.1";
  const expected = { durationMin: 127, durationMax: 201, bpmMin: 120, bpmMax: 141 };

  test("library", () => {
    expect(parseState(query)).toMatchObject(expected);
  });

  test("BeatSaver", () => {
    expect(parseBsState(query)).toMatchObject(expected);
  });

  test("playlists keep the Length rule", () => {
    expect(parsePlState("?duration_min=127.89&duration_max=200.2")).toMatchObject({
      durationMin: 127,
      durationMax: 201,
    });
  });

  test("decimal filters stay decimal", () => {
    expect(parseBsState("?nps_min=2.5")).toMatchObject({ npsMin: 2.5 });
  });
});

describe("fractional facet bounds", () => {
  const open = async (column: string) => {
    mockFetch((url) =>
      url.pathname === "/api/maps/facets"
        ? { ...FACETS, duration: { min: 127.89077, max: 300.2 }, bpm: { min: 90.4, max: 220.6 } }
        : { items: [item(1)], total: 1, offset: 0, limit: 40 },
    );
    const app = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    await userEvent.click(screen.getByRole("button", { name: new RegExp(`^Filter ${column}`) }));
    return { ...app, dialog: await screen.findByRole("dialog", { name: `${column} filter` }) };
  };
  const press = (el: HTMLElement) => {
    fireEvent.pointerDown(el, { button: 0 });
    fireEvent.pointerUp(el);
  };

  test("Length placeholders and the arrow start are whole seconds", async () => {
    const { dialog, router } = await open("Length");
    expect(within(dialog).getByLabelText("Minimum length")).toHaveAttribute("placeholder", "02:07");
    expect(within(dialog).getByLabelText("Maximum length")).toHaveAttribute("placeholder", "05:01");
    press(within(dialog).getByRole("button", { name: "Increase minimum length" }));
    await waitFor(() => expect(router.state.location.search).toContain("duration_min=128"));
    expect(router.state.location.search).not.toContain(".");
  });

  test("an arrow on an empty max starts from the rounded-up bound", async () => {
    const { dialog, router } = await open("Length");
    press(within(dialog).getByRole("button", { name: "Decrease maximum length" }));
    await waitFor(() => expect(router.state.location.search).toContain("duration_max=300"));
  });

  test("BPM placeholders floor the min and ceil the max; arrows write integers", async () => {
    const { dialog, router } = await open("BPM");
    expect(within(dialog).getByLabelText("BPM, at least")).toHaveAttribute("placeholder", "90");
    expect(within(dialog).getByLabelText("BPM, at most")).toHaveAttribute("placeholder", "221");
    press(within(dialog).getByRole("button", { name: "Increase minimum BPM" }));
    await waitFor(() => expect(router.state.location.search).toContain("bpm_min=91"));
  });
});
