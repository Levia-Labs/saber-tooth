import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import type { Proposal } from "../src/api/types";
import { TextFilterBody } from "../src/components/FilterBodies";
import { LONG_PRESS_MS, Tip, TipProvider } from "../src/components/Tip";
import { inlineText, item, mockFetch, renderApp, toasts } from "./helpers";

const realMatchMedia = window.matchMedia;
function touchDevice(on: boolean) {
  window.matchMedia = ((query: string) => ({
    ...realMatchMedia(query),
    matches: on && query === "(hover: none)",
  })) as typeof window.matchMedia;
}

afterEach(() => {
  window.matchMedia = realMatchMedia;
  vi.useRealTimers();
});

describe("touch tooltips", () => {
  const ui = () => (
    <TipProvider>
      <Tip text="Explains the button.">
        <button type="button">Scan</button>
      </Tip>
    </TipProvider>
  );

  test("a long press opens the tip and does not click the button", () => {
    touchDevice(true);
    vi.useFakeTimers();
    const clicked = vi.fn();
    render(
      <TipProvider>
        <Tip text="Explains the button.">
          <button type="button" onClick={clicked}>
            Scan
          </button>
        </Tip>
      </TipProvider>,
    );
    const button = screen.getByRole("button", { name: "Scan" });
    fireEvent.pointerDown(button, { pointerType: "touch" });
    act(() => {
      vi.advanceTimersByTime(LONG_PRESS_MS + 10);
    });
    expect(screen.getByRole("tooltip")).toHaveTextContent("Explains the button.");
    fireEvent.pointerUp(button, { pointerType: "touch" });
    fireEvent.click(button);
    expect(clicked).not.toHaveBeenCalled();
  });

  test("a short tap releases before the delay and shows nothing", () => {
    touchDevice(true);
    vi.useFakeTimers();
    render(ui());
    const button = screen.getByRole("button", { name: "Scan" });
    fireEvent.pointerDown(button, { pointerType: "touch" });
    fireEvent.pointerUp(button, { pointerType: "touch" });
    act(() => {
      vi.advanceTimersByTime(LONG_PRESS_MS * 2);
    });
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  test("no extra button is rendered on touch or on hover devices", () => {
    for (const touch of [true, false]) {
      touchDevice(touch);
      const { unmount } = render(ui());
      expect(screen.getAllByRole("button")).toHaveLength(1);
      unmount();
    }
  });

  test("a tap clicks the button and shows no tip", () => {
    touchDevice(true);
    vi.useFakeTimers();
    const clicked = vi.fn();
    render(
      <TipProvider>
        <Tip text="Explains the button.">
          <button type="button" onClick={clicked}>
            Scan
          </button>
        </Tip>
      </TipProvider>,
    );
    const button = screen.getByRole("button", { name: "Scan" });
    fireEvent.pointerDown(button, { pointerType: "touch" });
    fireEvent.pointerUp(button, { pointerType: "touch" });
    fireEvent.click(button);
    act(() => {
      vi.advanceTimersByTime(LONG_PRESS_MS * 2);
    });
    expect(clicked).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  test("the tip hides on release and the next tap clicks again", () => {
    touchDevice(true);
    vi.useFakeTimers();
    const clicked = vi.fn();
    render(
      <TipProvider>
        <Tip text="Explains the button.">
          <button type="button" onClick={clicked}>
            Scan
          </button>
        </Tip>
      </TipProvider>,
    );
    const button = screen.getByRole("button", { name: "Scan" });
    fireEvent.pointerDown(button, { pointerType: "touch" });
    act(() => {
      vi.advanceTimersByTime(LONG_PRESS_MS + 10);
    });
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    fireEvent.pointerUp(button, { pointerType: "touch" });
    fireEvent.click(button);
    expect(screen.queryByRole("tooltip")).toBeNull();
    expect(clicked).not.toHaveBeenCalled();
    fireEvent.pointerDown(button, { pointerType: "touch" });
    fireEvent.pointerUp(button, { pointerType: "touch" });
    fireEvent.click(button);
    expect(clicked).toHaveBeenCalledTimes(1);
  });

  test("scrolling hides an open tip", () => {
    touchDevice(true);
    vi.useFakeTimers();
    render(ui());
    fireEvent.pointerDown(screen.getByRole("button", { name: "Scan" }), { pointerType: "touch" });
    act(() => {
      vi.advanceTimersByTime(LONG_PRESS_MS + 10);
    });
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    fireEvent.scroll(window);
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  test("the wrapper turns off the native callout and keeps selection in inputs", () => {
    const css = readFileSync(resolve(__dirname, "../src/styles/overlays.css"), "utf-8");
    expect(css).toMatch(/\.tip-wrap \{[^}]*-webkit-touch-callout:\s*none[^}]*user-select:\s*none/);
    expect(css).toMatch(/\.tip-wrap :is\(input, textarea[^{]*\{[^}]*user-select:\s*text/);
  });
});

describe("title filter", () => {
  test("a search typed just before the popover closes is still sent", async () => {
    const onChange = vi.fn();
    const { unmount } = render(<TextFilterBody label="Title contains" q="" onChange={onChange} />);
    await userEvent.setup().type(screen.getByLabelText("Title contains"), "moon");
    expect(onChange).not.toHaveBeenCalled();
    unmount();
    expect(onChange).toHaveBeenCalledWith("moon", true);
  });
});

const proposal = (status: Proposal["status"]): Proposal => ({
  id: 1,
  rule: "flip-cut",
  difficulty: "Hard",
  severity: "error",
  summary: "Fix 1",
  status,
  before: [],
  after: [],
  walls_before: [],
  walls_after: [],
  walls_context: [],
});

function mapApiCalls(status: Proposal["status"] = "pending", failApprove = true) {
  return mockFetch((url, init) => {
    if (init?.method === "POST" && url.pathname.endsWith("/approve-all")) {
      return failApprove
        ? new Response(JSON.stringify({ error: "database is locked" }), { status: 409 })
        : { approved: 1 };
    }
    if (url.pathname === "/api/maps/id0000000001") return item(1);
    if (url.pathname.endsWith("/proposals")) return [proposal(status)];
    return {};
  });
}

function mapApi(status: Proposal["status"], failApprove = false) {
  mapApiCalls(status, failApprove);
}

describe("approve all", () => {
  test("shows the error instead of failing silently", async () => {
    mapApi("pending", true);
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await screen.findAllByText("Fix 1");
    await user.click(screen.getByRole("button", { name: "Approve all" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Approve all" }));
    expect(await toasts().findByText("Approve all failed")).toBeInTheDocument();
    expect(toasts().getByText(/database is busy/)).toBeInTheDocument();
    expect(toasts().getByText("database is locked")).toBeInTheDocument();
    expect(inlineText("Approve all failed")).toBe(false);
  });

  test("its Try again button in the toast posts approve-all again", async () => {
    const { fn } = mapApiCalls();
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await screen.findAllByText("Fix 1");
    await user.click(screen.getByRole("button", { name: "Approve all" }));
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", { name: "Approve all" }),
    );
    await toasts().findByText("Approve all failed");
    const posts = () => fn.mock.calls.filter(([u]) => String(u).endsWith("/approve-all")).length;
    expect(posts()).toBe(1);
    await user.click(toasts().getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(posts()).toBe(2));
  });

  test("updates the banner at once while the server is slow, and rolls back on failure", async () => {
    let release: (r: Response) => void = () => {};
    const gate = new Promise<Response>((r) => (release = r));
    mockFetch((url, init) => {
      if (init?.method === "POST" && url.pathname.endsWith("/approve-all")) return gate;
      if (url.pathname === "/api/maps/id0000000001") return item(1);
      if (url.pathname.endsWith("/proposals")) return [proposal("pending")];
      return {};
    });
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await screen.findAllByText("Fix 1");
    expect(screen.getByText("No fixes approved yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Approve all" }));
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", { name: "Approve all" }),
    );
    await waitFor(() => expect(screen.queryByText("No fixes approved yet")).toBeNull());
    expect(screen.getByRole("button", { name: "Apply approved" })).toBeEnabled();
    release(new Response(JSON.stringify({ error: "database is locked" }), { status: 409 }));
    await toasts().findByText("Approve all failed");
    expect(await screen.findByText("No fixes approved yet")).toBeInTheDocument();
  });

  test("is disabled when nothing is pending", async () => {
    mapApi("approved");
    renderApp("/maps/id0000000001");
    await screen.findAllByText("Fix 1");
    await waitFor(() => expect(screen.getByRole("button", { name: "Approve all" })).toBeDisabled());
  });
});
