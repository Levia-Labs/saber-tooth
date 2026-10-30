import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { CropPanel } from "../src/components/CropPanel";
import { SUGGESTIONS, cropApi, endHandle, renderPanel, startHandle } from "./crophelpers";

function setup(options = {}) {
  const api = cropApi(options);
  renderPanel(<CropPanel mapId="id0000000001" folder="Folder 1" busy={false} />);
  return { ...api, user: userEvent.setup() };
}

const proposals = () => screen.findByRole("radiogroup", { name: "Auto crop proposals" });

describe("Auto crop", () => {
  test("Auto is first and selected by default, with three proposal cards", async () => {
    setup();
    const row = await screen.findByRole("radiogroup", { name: "Crop length" });
    const radios = within(row).getAllByRole("radio");
    expect(radios.map((r) => r.textContent)).toEqual(["Auto", "1 min", "2 min", "Unlimited"]);
    expect(radios[0]).toBeChecked();
    const cards = within(await proposals()).getAllByRole("radio");
    expect(cards).toHaveLength(3);
    expect(cards[0]).toBeChecked();
    expect(cards[0]).toHaveTextContent("#1");
    expect(cards[0]).toHaveTextContent("0:00.0 to 1:04.0");
    expect(cards[0]).toHaveTextContent("Score 90");
  });

  test("shows a spinner while the proposals load", async () => {
    let release: (value: unknown) => void = () => {};
    setup({ suggestions: new Promise((resolve) => (release = resolve)) });
    expect(await screen.findByRole("status", { name: "Finding the best crops" })).toBeVisible();
    release(SUGGESTIONS);
    expect(await proposals()).toBeInTheDocument();
  });

  test("selecting a proposal sets the crop window", async () => {
    const { user } = setup();
    await user.click(within(await proposals()).getAllByRole("radio")[1] as HTMLElement);
    await waitFor(() => expect(startHandle()).toHaveAttribute("aria-valuenow", "70"));
    expect(endHandle()).toHaveAttribute("aria-valuenow", "136");
  });

  test("the saved crop uses the selected proposal", async () => {
    const { user, posts } = setup();
    await user.click(within(await proposals()).getAllByRole("radio")[2] as HTMLElement);
    await user.click(screen.getByRole("button", { name: "Save as new map" }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]?.body).toMatchObject({ start_s: 10, end_s: 130 });
  });

  test("no candidate shows an empty state and a custom fallback", async () => {
    const { user } = setup({
      suggestions: {
        map_id: "x",
        duration_s: 40,
        reason: "The song is 40 s long.",
        suggestions: [],
      },
    });
    expect(await screen.findByText("No automatic crop fits this song")).toBeInTheDocument();
    expect(screen.getByText("The song is 40 s long.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Custom crop" }));
    expect(screen.getByRole("radio", { name: "Unlimited" })).toBeChecked();
  });

  test("1 min still works after Auto", async () => {
    const { user } = setup();
    await proposals();
    await user.click(screen.getByRole("radio", { name: "1 min" }));
    expect(screen.queryByRole("radiogroup", { name: "Auto crop proposals" })).toBeNull();
    expect(endHandle()).toHaveAttribute("aria-valuenow", "64");
  });
});
