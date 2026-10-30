import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useLocation } from "react-router";
import { describe, expect, test } from "vitest";
import { CropPanel } from "../src/components/CropPanel";
import { cropApi, renderPanel } from "./crophelpers";

function Where() {
  const loc = useLocation();
  return <output data-testid="where">{loc.pathname + loc.search}</output>;
}

async function setup(route: string) {
  const api = cropApi();
  renderPanel(
    <>
      <CropPanel mapId="id0000000001" folder="Folder 1" busy={false} />
      <Where />
    </>,
    route,
  );
  await within(
    await screen.findByRole("radiogroup", { name: "Auto crop proposals" }),
  ).findAllByRole("radio");
  return { ...api, user: userEvent.setup() };
}

const where = () => screen.getByTestId("where").textContent;
const count = (calls: URL[], tail: string) => calls.filter((u) => u.pathname.endsWith(tail)).length;

describe("after a crop finishes", () => {
  test("save as new map opens the new map on Status, keeping the origin", async () => {
    const { user } = await setup("/maps/id0000000001?tab=crop&from=jobs&back=status%3Ddone");
    await user.click(screen.getByRole("button", { name: "Save as new map" }));
    await waitFor(() => expect(where()).toBe("/maps/id0000000099?from=jobs&back=status%3Ddone"));
  });

  test("save over this map goes to Status and refetches suggestions and timeline", async () => {
    const { user, calls } = await setup("/maps/id0000000001?tab=crop&from=jobs");
    expect(count(calls, "/crop/suggestions")).toBe(1);
    await user.click(screen.getByRole("button", { name: "Save over this map" }));
    await user.click(await screen.findByRole("button", { name: "Replace map" }));
    await waitFor(() => expect(where()).toBe("/maps/id0000000001?from=jobs"));
    await waitFor(() => expect(count(calls, "/timeline")).toBeGreaterThan(1));
    expect(count(calls, "/crop/suggestions")).toBeGreaterThan(1);
  });

  test("the crop state resets: old proposals are gone until new ones load", async () => {
    const { user } = await setup("/maps/id0000000001?tab=crop");
    await user.click(screen.getByRole("button", { name: "Save over this map" }));
    await user.click(await screen.findByRole("button", { name: "Replace map" }));
    await waitFor(() => expect(where()).toBe("/maps/id0000000001"));
    expect(screen.getByRole("radio", { name: "Auto" })).toBeChecked();
  });
});
