import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { cropApi } from "./crophelpers";
import { renderApp } from "./helpers";

describe("crop panel on the map page", () => {
  test("is offered on a map, and the timeline loads only when it is opened", async () => {
    const { calls } = cropApi();
    renderApp("/maps/id0000000001");
    const toggle = await screen.findByRole("button", { name: /Crop to 1 or 2 minutes/ });
    expect(calls.some((u) => u.pathname.endsWith("/timeline"))).toBe(false);
    await userEvent.setup().click(toggle);
    expect(await screen.findByRole("slider", { name: "Crop end" })).toBeInTheDocument();
  });

  test("Create is disabled while a job runs on the map", async () => {
    cropApi({ map: { status: "scanning", job: { id: "j", kind: "scan", status: "running" } } });
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /Crop to 1 or 2 minutes/ }));
    await screen.findByRole("slider", { name: "Crop end" });
    expect(screen.getByRole("button", { name: "Create cropped map" })).toBeDisabled();
  });

  test("is not offered on an unreadable map", async () => {
    cropApi({ map: { status: "unreadable", parse_error: "bad json" } });
    renderApp("/maps/id0000000001");
    await screen.findByRole("heading", { level: 1 });
    expect(screen.queryByRole("button", { name: /Crop to 1 or 2 minutes/ })).toBeNull();
  });
});
