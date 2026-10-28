import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { CropPanel } from "../src/components/CropPanel";
import { moveWindowToSection, sectionStep } from "../src/lib/crop";
import { cropApi, endHandle, renderPanel, startHandle } from "./crophelpers";

type User = ReturnType<typeof userEvent.setup>;

async function setup(props: { steps?: boolean } = { steps: true }) {
  const api = cropApi();
  renderPanel(<CropPanel mapId="id0000000001" folder="Folder 1" busy={false} {...props} />);
  await screen.findByRole("slider", { name: "Crop end" });
  return { ...api, user: userEvent.setup() };
}

async function press(user: User, name: string, times = 1) {
  for (let i = 0; i < times; i++) await user.click(screen.getByRole("button", { name }));
}

const at = (handle: HTMLElement) => Number(handle.getAttribute("aria-valuenow"));

/** Switch to 2 min: the window is 0 s to 112 s, so every section start can be reached. */
const twoMinutes = (user: User) => user.click(screen.getByRole("radio", { name: "2 min" }));

describe("CropPanel steps", () => {
  test("the step buttons are off unless asked for", async () => {
    await setup({});
    expect(screen.queryByRole("group", { name: "Move the crop" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Next section" })).toBeNull();
  });

  test("four large step buttons appear, each with its help as text", async () => {
    await setup();
    const group = screen.getByRole("group", { name: "Move the crop" });
    for (const name of ["Previous section", "Next section", "End 1 s earlier", "End 1 s later"]) {
      expect(within(group).getByRole("button", { name })).toBeEnabled();
    }
    expect(group).toHaveTextContent("Move the start to the previous section.");
    expect(group).toHaveTextContent("Move the end one second later.");
  });

  test("the end moves one second a press, both ways", async () => {
    const { user } = await setup();
    expect(at(endHandle())).toBe(64);
    await press(user, "End 1 s later", 2);
    expect(at(endHandle())).toBe(66);
    await press(user, "End 1 s earlier", 3);
    expect(at(endHandle())).toBe(63);
  });

  test("Next section moves the whole 1 min window to the next boundary, same length", async () => {
    const { user } = await setup();
    await press(user, "Next section");
    expect([at(startHandle()), at(endHandle())]).toEqual([64, 128]);
    await press(user, "Previous section");
    expect([at(startHandle()), at(endHandle())]).toEqual([0, 64]);
  });

  test("a window cut by the song end is shortened, never below a second", async () => {
    const { user } = await setup();
    await twoMinutes(user);
    await press(user, "Next section");
    expect([at(startHandle()), at(endHandle())]).toEqual([64, 140]);
    await press(user, "Next section");
    expect([at(startHandle()), at(endHandle())]).toEqual([112, 140]);
    await press(user, "Next section");
    expect([at(startHandle()), at(endHandle())]).toEqual([112, 140]);
    await press(user, "Previous section");
    expect([at(startHandle()), at(endHandle())]).toEqual([64, 92]);
  });

  test("step buttons stay put at the first section and the song start", async () => {
    const { user } = await setup();
    await press(user, "Previous section");
    expect([at(startHandle()), at(endHandle())]).toEqual([0, 64]);
    await twoMinutes(user);
    await press(user, "Next section", 2);
    await press(user, "Previous section", 5);
    expect(at(startHandle())).toBe(0);
  });

  test("the end stops at the end of the song", async () => {
    const { user } = await setup();
    await twoMinutes(user);
    await press(user, "End 1 s later", 40);
    expect(at(endHandle())).toBe(140);
  });

  test("Save as new map and Save over this map post the stepped window", async () => {
    const { user, posts } = await setup();
    await twoMinutes(user);
    await press(user, "Next section");
    await press(user, "Save as new map");
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]?.body).toEqual({ start_s: 64, end_s: 140 });
    await user.click(screen.getByRole("button", { name: "Save over this map" }));
    await user.click(await screen.findByRole("button", { name: "Replace map" }));
    await waitFor(() => expect(posts).toHaveLength(2));
    expect(posts[1]?.body).toEqual({ start_s: 64, end_s: 140, replace: true });
  });
});

describe("moveWindowToSection", () => {
  const starts = [0, 64, 112];

  test("keeps the length, shortens at the song end and stays put without a boundary", () => {
    const win = { start_s: 0, end_s: 64 };
    expect(moveWindowToSection(win, starts, 1, 1, 140)).toEqual({ start_s: 64, end_s: 128 });
    expect(moveWindowToSection(win, starts, -1, 1, 140)).toEqual(win);
    expect(moveWindowToSection({ start_s: 64, end_s: 128 }, starts, 1, 1, 140)).toEqual({
      start_s: 112,
      end_s: 140,
    });
    expect(moveWindowToSection(win, [0, 139.5], 1, 1, 140)).toEqual({ start_s: 139, end_s: 140 });
  });

  test("always stays inside the song, at least min long and never grows", () => {
    fc.assert(
      fc.property(
        fc.array(fc.double({ min: 0, max: 140, noNaN: true }), { maxLength: 8 }),
        fc.double({ min: 0, max: 100, noNaN: true }),
        fc.double({ min: 1, max: 40, noNaN: true }),
        fc.constantFrom(1 as const, -1 as const),
        (list, start, length, dir) => {
          const win = { start_s: start, end_s: start + length };
          const out = moveWindowToSection(win, list, dir, 1, 140);
          expect(out.start_s).toBeGreaterThanOrEqual(0);
          expect(out.end_s).toBeLessThanOrEqual(140);
          expect(out.end_s - out.start_s).toBeGreaterThanOrEqual(1 - 1e-3);
          expect(out.end_s - out.start_s).toBeLessThanOrEqual(length + 1e-3);
        },
      ),
    );
  });
});

describe("sectionStep", () => {
  const starts = [0, 64, 112];

  test("finds the next and previous boundary, or null at the edges", () => {
    expect(sectionStep(starts, 0, 1)).toBe(64);
    expect(sectionStep(starts, 64, 1)).toBe(112);
    expect(sectionStep(starts, 112, 1)).toBeNull();
    expect(sectionStep(starts, 70, -1)).toBe(64);
    expect(sectionStep(starts, 0, -1)).toBeNull();
    expect(sectionStep([], 5, 1)).toBeNull();
  });

  test("always moves strictly in the asked direction onto a listed boundary", () => {
    fc.assert(
      fc.property(
        fc.array(fc.double({ min: 0, max: 600, noNaN: true }), { maxLength: 12 }),
        fc.double({ min: 0, max: 600, noNaN: true }),
        fc.constantFrom(1 as const, -1 as const),
        (list, from, dir) => {
          const out = sectionStep(list, from, dir);
          if (out === null) return;
          expect(list).toContain(out);
          expect(dir * (out - from)).toBeGreaterThan(0);
        },
      ),
    );
  });
});
