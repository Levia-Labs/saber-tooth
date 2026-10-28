import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { MapItem } from "../src/api/types";
import { TIPS } from "../src/lib/tips";
import { VrMapPage } from "../src/vr/VrMapPage";
import { TIMELINE } from "./crophelpers";
import { item, mockFetch } from "./helpers";
import { renderVr } from "./vrhelpers";

const ID = "id0000000001";

function mapApi(patch: Partial<MapItem> = {}, map: unknown = item(1, patch)) {
  const posts: { path: string; body: unknown }[] = [];
  const mock = mockFetch((url, init) => {
    if (init?.method === "DELETE") return { deleted: "Folder 1" };
    if (init?.method === "POST") {
      posts.push({ path: url.pathname, body: JSON.parse(String(init.body ?? "{}")) });
      return { job: "j" };
    }
    if (url.pathname === `/api/maps/${ID}`) return map;
    if (url.pathname === `/api/maps/${ID}/timeline`) return TIMELINE;
    if (url.pathname.startsWith("/api/jobs/")) {
      return { id: "j", kind: "fix", status: "running", error: null, result: null };
    }
    return {};
  });
  return { ...mock, posts };
}

const show = () => renderVr(`/vr/maps/${ID}`, "/vr/maps/:id", <VrMapPage />);
const sent = (fn: ReturnType<typeof mapApi>["fn"], method: string, path: string) =>
  fn.mock.calls.some(([url, init]) => String(url) === path && init?.method === method);

describe("VR map screen", () => {
  test("shows the header, status and a way back to the VR library", async () => {
    mapApi({ status: "error", errors: 3, mapper: "Ada" });
    show();
    expect(await screen.findByRole("heading", { name: "Song 1" })).toBeInTheDocument();
    expect(screen.getByText(/Ada/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "3 errors" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Library/ })).toHaveAttribute("href", "/vr");
  });

  test("a large Fix starts the fix job and explains itself as text", async () => {
    const { fn } = mapApi();
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: "Fix" }));
    await waitFor(() => expect(sent(fn, "POST", `/api/maps/${ID}/fix`)).toBe(true));
    expect(screen.getByText(TIPS.fix)).toBeInTheDocument();
  });

  test("a fixed copy needs no Fix and links back to its original", async () => {
    mapApi({
      status: "ok",
      folder: "Folder 1 [saber-tooth]",
      original_id: "id0000000009",
      original_folder: "Folder 1",
    });
    show();
    expect(await screen.findByText("Fixed copy of")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Fix" })).toBeNull();
  });

  test("Fix and Delete are off while a job runs on the map", async () => {
    mapApi({ job: { id: "j", kind: "scan", status: "running" }, status: "scanning" });
    show();
    expect(await screen.findByRole("button", { name: "Fix" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
  });

  test("Delete asks first and Cancel deletes nothing", async () => {
    const { fn } = mapApi();
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete permanently?" });
    expect(dialog).toHaveTextContent('"Folder 1" is removed from disk and cannot be undone.');
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(sent(fn, "DELETE", `/api/maps/${ID}`)).toBe(false);
    expect(screen.getByText(TIPS.delete)).toBeInTheDocument();
  });

  test("confirming Delete removes the map and returns to the VR library", async () => {
    const { fn } = mapApi();
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete permanently?" });
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(sent(fn, "DELETE", `/api/maps/${ID}`)).toBe(true));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/vr$/));
  });

  test("the crop panel is there with the step buttons and both save buttons", async () => {
    mapApi();
    show();
    expect(await screen.findByRole("radio", { name: "1 min" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "2 min" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Unlimited" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Move the crop" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save as new map" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Save over this map" })).toBeEnabled();
  });

  test("a stepped crop is saved over this map after the confirmation", async () => {
    const { posts } = mapApi();
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: "End 1 s later" }));
    await user.click(screen.getByRole("button", { name: "Save over this map" }));
    await user.click(await screen.findByRole("button", { name: "Replace map" }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toEqual({
      path: `/api/maps/${ID}/crop`,
      body: { start_s: 0, end_s: 65, replace: true },
    });
  });

  test("an unknown map says so", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify({ error: "no such map" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        }),
    );
    show();
    expect(await screen.findByText("Map not found")).toBeInTheDocument();
  });

  test("a map that cannot be loaded shows an alert", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify({ error: "bad" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }),
    );
    show();
    expect(await screen.findByText("Could not load the map")).toBeInTheDocument();
  });
});
