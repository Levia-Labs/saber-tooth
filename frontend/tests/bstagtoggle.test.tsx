import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { bsApi, bsMap, page } from "./bshelpers";
import { renderApp } from "./helpers";

describe("BeatSaver tag chips toggle the tags filter", () => {
  const setup = (path: string) => {
    const urls: URL[] = [];
    bsApi({
      search: (u) => {
        urls.push(u);
        return page([bsMap(2, { tags: ["rock", "pop"] })]);
      },
    });
    renderApp(path);
    return urls;
  };

  test("clicking an inactive tag adds it and refetches", async () => {
    const urls = setup("/beatsaver");
    const chip = await screen.findByRole("button", { name: "rock" });
    expect(chip).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(chip);
    await waitFor(() => expect(urls.at(-1)?.searchParams.get("tags")).toBe("rock"));
    expect(await screen.findByRole("button", { name: "rock" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "pop" })).toHaveAttribute("aria-pressed", "false");
  });

  test("clicking an active tag removes it", async () => {
    const urls = setup("/beatsaver?tags=rock");
    const chip = await screen.findByRole("button", { name: "rock" });
    expect(chip).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(chip);
    await waitFor(() => expect(urls.at(-1)?.searchParams.get("tags")).toBeNull());
    expect(await screen.findByRole("button", { name: "rock" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  test("tips say Filter by and Remove filter", async () => {
    setup("/beatsaver?tags=rock");
    await userEvent.hover(await screen.findByRole("button", { name: "rock" }));
    expect((await screen.findAllByText("Remove rock filter")).length).toBeGreaterThan(0);
    await userEvent.hover(screen.getByRole("button", { name: "pop" }));
    expect((await screen.findAllByText("Filter by pop")).length).toBeGreaterThan(0);
  });
});
