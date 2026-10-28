import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { cropApi } from "./crophelpers";
import { renderApp } from "./helpers";

describe("crop panel on the map page", () => {
  test("is offered as a tab, and the timeline loads only when it is shown", async () => {
    const { calls } = cropApi();
    renderApp("/maps/id0000000001");
    const tab = await screen.findByRole("tab", { name: "Crop" });
    expect(calls.some((u) => u.pathname.endsWith("/timeline"))).toBe(false);
    await userEvent.setup().click(tab);
    expect(await screen.findByRole("slider", { name: "Crop end" })).toBeInTheDocument();
  });

  test("Save as new map is disabled while a job runs on the map", async () => {
    cropApi({ map: { status: "scanning", job: { id: "j", kind: "scan", status: "running" } } });
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("tab", { name: "Crop" }));
    await screen.findByRole("slider", { name: "Crop end" });
    expect(screen.getByRole("button", { name: "Save as new map" })).toBeDisabled();
  });

  test("is not offered on an unreadable map", async () => {
    cropApi({ map: { status: "unreadable", parse_error: "bad json" } });
    renderApp("/maps/id0000000001");
    await screen.findByRole("heading", { level: 1 });
    await screen.findByRole("tablist");
    expect(screen.queryByRole("tab", { name: "Crop" })).toBeNull();
  });
});
