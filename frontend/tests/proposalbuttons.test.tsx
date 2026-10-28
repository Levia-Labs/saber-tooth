import { screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { Proposal } from "../src/api/types";
import { canApprove, canReject } from "../src/lib/decisions";
import { item, mockFetch, renderApp } from "./helpers";

describe("proposal decision states", () => {
  test.each([
    ["pending", true, true],
    ["rejected", true, false],
    ["approved", false, true],
    ["applying", false, false],
    ["applied", false, false],
    ["superseded", false, false],
  ] as const)("%s: approve %s, reject %s", (status, approve, reject) => {
    expect(canApprove(status)).toBe(approve);
    expect(canReject(status)).toBe(reject);
  });
});

describe("proposal card buttons", () => {
  const note = { beat: 4, x: 1, y: 0, color: 0, cut: 1 };
  const make = (id: number, status: Proposal["status"]): Proposal => ({
    id,
    rule: "flip-cut",
    difficulty: "Hard",
    severity: "error",
    summary: `Fix ${id}`,
    status,
    before: [note],
    after: [{ ...note, cut: 0 }],
    walls_before: [],
    walls_after: [],
    walls_context: [],
  });

  test("approved keeps Reject for undo; applied and superseded disable both", async () => {
    mockFetch((url) => {
      if (url.pathname === "/api/maps/id0000000001") return item(1);
      if (url.pathname.endsWith("/proposals")) {
        return [make(1, "approved"), make(2, "applied"), make(3, "superseded"), make(4, "pending")];
      }
      return {};
    });
    renderApp("/maps/id0000000001");
    const state = async (n: number) => {
      const card = (await screen.findByText(`Fix ${n}`)).closest("article") as HTMLElement;
      const q = within(card);
      return [
        q.getByRole("button", { name: "Approve" }),
        q.getByRole("button", { name: "Reject" }),
      ].map((b) => (b as HTMLButtonElement).disabled);
    };
    expect(await state(1)).toEqual([true, false]);
    expect(await state(2)).toEqual([true, true]);
    expect(await state(3)).toEqual([true, true]);
    expect(await state(4)).toEqual([false, false]);
  });
});
