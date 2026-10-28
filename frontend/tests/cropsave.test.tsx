import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { CropPanel } from "../src/components/CropPanel";
import { cropApi, renderPanel } from "./crophelpers";
import { renderApp } from "./helpers";

const OVER = { name: "Save over this map" };

async function setup(busy = false) {
  const api = cropApi();
  renderPanel(<CropPanel mapId="id0000000001" folder="Folder 1" busy={busy} />);
  await screen.findByRole("slider", { name: "Crop end" });
  return { ...api, user: userEvent.setup() };
}

describe("Save over this map", () => {
  test("sits next to Save as new map and opens the replace confirmation", async () => {
    const { user } = await setup();
    const over = screen.getByRole("button", OVER);
    expect(over).toHaveClass("warning");
    const save = screen.getByRole("button", { name: "Save as new map" });
    expect(over.parentElement).toBe(save.parentElement);
    await user.click(over);
    const dialog = await screen.findByRole("dialog", { name: "Replace this map?" });
    expect(dialog).toHaveTextContent('"Folder 1"');
    expect(dialog).toHaveTextContent("replaced by the cropped version");
    expect(dialog).toHaveTextContent("cannot be restored");
    expect(within(dialog).getByRole("button", { name: "Replace map" })).toHaveClass("danger");
  });

  test("Cancel posts nothing", async () => {
    const { user, posts } = await setup();
    await user.click(screen.getByRole("button", OVER));
    await user.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(posts).toHaveLength(0);
  });

  test("confirming posts replace: true with seconds and announces Map replaced", async () => {
    const { user, posts } = await setup();
    await user.click(screen.getByRole("button", OVER));
    await user.click(await screen.findByRole("button", { name: "Replace map" }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]?.body).toEqual({ start_s: 0, end_s: 64, replace: true });
    expect(await screen.findByText("Map replaced")).toBeInTheDocument();
  });

  test("Save as new map posts seconds only", async () => {
    const { user, posts } = await setup();
    await user.click(screen.getByRole("button", { name: "Save as new map" }));
    await waitFor(() => expect(posts[0]?.body).toEqual({ start_s: 0, end_s: 64 }));
  });

  test("is not shown while a job runs on the map", async () => {
    await setup(true);
    expect(screen.queryByRole("button", OVER)).toBeNull();
    expect(screen.getByRole("button", { name: "Save as new map" })).toBeDisabled();
  });

  test("a successful replace refreshes the map page", async () => {
    const { calls } = cropApi();
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("tab", { name: "Crop" }));
    await screen.findByRole("slider", { name: "Crop end" });
    const loads = () => calls.filter((u) => u.pathname === "/api/maps/id0000000001").length;
    const before = loads();
    await user.click(screen.getByRole("button", OVER));
    await user.click(await screen.findByRole("button", { name: "Replace map" }));
    await waitFor(() => expect(loads()).toBeGreaterThan(before));
  });
});
