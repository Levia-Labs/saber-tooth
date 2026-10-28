import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { MapItem } from "../src/api/types";
import { formatDuration } from "../src/lib/format";
import { VrLibraryPage } from "../src/vr/VrLibraryPage";
import { item, mockFetch } from "./helpers";
import { renderVr, stubObserver } from "./vrhelpers";

function library(items: MapItem[], total = items.length) {
  return mockFetch((url, init) => {
    if (url.pathname === "/api/maps") {
      const offset = Number(url.searchParams.get("offset") ?? "0");
      return { items: items.slice(offset, offset + 2), total, offset, limit: 2 };
    }
    if (url.pathname.startsWith("/api/jobs/")) {
      return { id: "j", kind: "fix", status: "running", error: null, result: null };
    }
    return init?.method === "POST" ? { job: "j" } : {};
  });
}

const mapsCalls = (calls: URL[]) => calls.filter((u) => u.pathname === "/api/maps");
const last = (calls: URL[]) => mapsCalls(calls).at(-1)!.searchParams;

function show(url = "/vr") {
  return renderVr(url, "/vr", <VrLibraryPage />);
}

describe("VR library cards", () => {
  test("a card shows the cover area, title, status, levels and length with its actions", async () => {
    const song = item(1, {
      status: "error",
      errors: 2,
      audio_url: "/api/maps/id0000000001/audio",
      duration_s: 201,
    });
    library([song, item(2)]);
    show();
    const card = (await screen.findByRole("heading", { name: "Song 1" })).closest("article")!;
    expect(within(card).getByRole("img", { name: "2 errors" })).toBeInTheDocument();
    expect(within(card).getByText(formatDuration(201))).toBeInTheDocument();
    expect(
      within(card).getByRole("button", { name: "Play preview of Song 1" }),
    ).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Fix Song 1" })).toBeEnabled();
    expect(within(card).getByRole("link", { name: "Open Song 1" })).toHaveAttribute(
      "href",
      "/vr/maps/id0000000001",
    );
  });

  test("a map that has a fixed copy offers Open fixed copy", async () => {
    library([
      item(1, { fixed_copy_id: "id0000000099", fixed_copy_folder: "Folder 1 [saber-tooth]" }),
    ]);
    show();
    const link = await screen.findByRole("link", { name: "Open fixed copy of Song 1" });
    expect(link).toHaveAttribute("href", "/vr/maps/id0000000099");
    expect(screen.queryByRole("link", { name: "Open Song 1" })).toBeNull();
  });

  test("Fix starts the fix job for that map", async () => {
    const { fn } = library([item(1)]);
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: "Fix Song 1" }));
    await waitFor(() =>
      expect(
        fn.mock.calls.some(
          ([url, init]) => String(url) === "/api/maps/id0000000001/fix" && init?.method === "POST",
        ),
      ).toBe(true),
    );
  });

  test("a map with a running job or an unreadable Info file cannot be fixed again", async () => {
    library([item(1, { status: "unreadable", parse_error: "bad json" })]);
    show();
    expect(await screen.findByRole("button", { name: "Fix Song 1" })).toBeDisabled();
  });

  test("the screen offers no text search and every control states its help as text", async () => {
    library([item(1)]);
    show();
    await screen.findByRole("heading", { name: "Song 1" });
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("searchbox")).toBeNull();
    expect(screen.getByText("Maps with errors or warnings.")).toBeInTheDocument();
  });

  test("the section links lead to the VR library and the VR BeatSaver screen", async () => {
    library([item(1)]);
    show();
    const nav = await screen.findByRole("navigation", { name: "Section" });
    expect(within(nav).getByRole("link", { name: "Library" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(nav).getByRole("link", { name: "BeatSaver" })).toHaveAttribute(
      "href",
      "/vr/beatsaver",
    );
  });
});

describe("VR library presets and sort", () => {
  test.each([
    ["Needs fix", "status", "error,warn"],
    ["Missing levels", "status", "incomplete"],
    ["Not scanned", "status", "unscanned"],
  ])("%s asks for %s=%s", async (label, key, expected) => {
    const { calls } = library([item(1)]);
    const user = userEvent.setup();
    show();
    await screen.findByRole("heading", { name: "Song 1" });
    await user.click(screen.getByRole("button", { name: label }));
    await waitFor(() => expect(last(calls).get(key)).toBe(expected));
    expect(screen.getByRole("button", { name: label })).toHaveAttribute("aria-pressed", "true");
  });

  test("Expert+ asks for the ExpertPlus level and combines with a status preset", async () => {
    const { calls } = library([item(1)]);
    const user = userEvent.setup();
    show();
    await screen.findByRole("heading", { name: "Song 1" });
    await user.click(screen.getByRole("button", { name: "Needs fix" }));
    await user.click(screen.getByRole("button", { name: "Expert+" }));
    await waitFor(() => expect(last(calls).getAll("level")).toEqual(["ExpertPlus"]));
    expect(last(calls).get("status")).toBe("error,warn");
    expect(screen.getByTestId("where")).toHaveTextContent("/vr?p=needs-fix%2Cexpert-plus");
  });

  test("turning a preset off restores the unfiltered query", async () => {
    const { calls } = library([item(1)]);
    const user = userEvent.setup();
    show();
    await screen.findByRole("heading", { name: "Song 1" });
    await user.click(screen.getByRole("button", { name: "Not scanned" }));
    await waitFor(() => expect(last(calls).get("status")).toBe("unscanned"));
    await user.click(screen.getByRole("button", { name: "Not scanned" }));
    // The unfiltered list is still cached, so no new request is made; the address and button show it.
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/vr$/));
    expect(screen.getByRole("button", { name: "Not scanned" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(mapsCalls(calls)[0]!.searchParams.get("status")).toBeNull();
    expect(await screen.findByRole("heading", { name: "Song 1" })).toBeInTheDocument();
  });

  test("Fixed copies keeps only maps with an original, in the browser", async () => {
    const { calls } = library([item(1), item(2, { original_id: "id0000000001", status: "ok" })]);
    const user = userEvent.setup();
    show();
    await screen.findByRole("heading", { name: "Song 2" });
    await user.click(screen.getByRole("button", { name: "Fixed copies" }));
    expect(screen.queryByRole("heading", { name: "Song 1" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Song 2" })).toBeInTheDocument();
    expect(last(calls).get("status")).toBeNull();
  });

  test("Fixed copies counts the loaded matching cards, without the server total", async () => {
    library([item(1), item(2, { original_id: "id0000000001", status: "ok" })], 7);
    const user = userEvent.setup();
    show();
    await screen.findByRole("heading", { name: "Song 2" });
    expect(screen.getByText("7 maps")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fixed copies" }));
    expect(screen.getByText("1 map")).toBeInTheDocument();
    expect(screen.queryByText(/of 7|7 maps/)).toBeNull();
  });

  test("Fixed copies keeps fetching pages while none of the loaded cards match", async () => {
    const maps = [item(1), item(2), item(3, { original_id: "id0000000001", status: "ok" })];
    const observer = stubObserver();
    const { calls } = library(maps, 3);
    const user = userEvent.setup();
    show("/vr?p=fixed");
    await waitFor(() => expect(mapsCalls(calls)).toHaveLength(1));
    await screen.findByText("0 maps");
    expect(screen.queryByText(/No maps match/)).toBeNull();
    observer.fire();
    expect(await screen.findByRole("heading", { name: "Song 3" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Song 1" })).toBeNull();
    expect(screen.getByText("1 map")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fixed copies" }));
    expect(screen.getByRole("heading", { name: "Song 1" })).toBeInTheDocument();
  });

  test("the sort choice asks the API for that order", async () => {
    const { calls } = library([item(1)]);
    const user = userEvent.setup();
    show();
    await screen.findByRole("heading", { name: "Song 1" });
    expect(screen.getByRole("radio", { name: "Title" })).toBeChecked();
    await user.click(screen.getByRole("radio", { name: "Most errors" }));
    await waitFor(() => expect(last(calls).get("sort")).toBe("errors"));
    expect(last(calls).get("order")).toBe("desc");
    expect(screen.getByRole("radio", { name: "Most errors" })).toBeChecked();
  });

  test("the address restores the presets and ignores unknown values", async () => {
    const { calls } = library([item(1)]);
    show("/vr?p=needs-fix,bogus&sort=nope");
    await screen.findByRole("heading", { name: "Song 1" });
    expect(mapsCalls(calls)[0]!.searchParams.get("status")).toBe("error,warn");
    expect(mapsCalls(calls)[0]!.searchParams.get("sort")).toBe("title");
    expect(screen.getByRole("button", { name: "Needs fix" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});

describe("VR library loading", () => {
  test("the next page loads when the end of the list scrolls into view", async () => {
    const maps = [item(1), item(2), item(3)];
    const observer = stubObserver();
    const { calls } = library(maps, 3);
    show();
    await screen.findByRole("heading", { name: "Song 2" });
    expect(screen.queryByRole("heading", { name: "Song 3" })).toBeNull();
    observer.fire();
    expect(await screen.findByRole("heading", { name: "Song 3" })).toBeInTheDocument();
    expect(mapsCalls(calls).map((u) => u.searchParams.get("offset"))).toEqual(["0", "2"]);
  });

  test("a failed list shows an alert", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify({ error: "bad query" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }),
    );
    show();
    expect(await screen.findByText("Could not load the library")).toBeInTheDocument();
  });

  test("an empty result says so", async () => {
    library([]);
    show();
    expect(await screen.findByText(/No maps match/)).toBeInTheDocument();
  });
});
