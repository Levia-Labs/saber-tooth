import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import type { Proposal } from "../src/api/types";
import { TextFilterBody } from "../src/components/FilterBodies";
import { LONG_PRESS_MS, Tip, TipProvider } from "../src/components/Tip";
import { item, mockFetch, renderApp } from "./helpers";

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
      <Tip text="Explains the button." info>
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

  test("the info button opens the same copy on tap", async () => {
    touchDevice(true);
    render(ui());
    await userEvent.setup().click(screen.getByRole("button", { name: "What does this do?" }));
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Explains the button.");
  });

  test("no info button on devices that can hover", () => {
    touchDevice(false);
    render(ui());
    expect(screen.queryByRole("button", { name: "What does this do?" })).toBeNull();
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

function mapApi(status: Proposal["status"], failApprove = false) {
  mockFetch((url, init) => {
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

describe("approve all", () => {
  test("shows the error instead of failing silently", async () => {
    mapApi("pending", true);
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await screen.findAllByText("Fix 1");
    await user.click(screen.getByRole("button", { name: "Approve all" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Approve all" }));
    expect(await screen.findByText("Approve all failed")).toBeInTheDocument();
    expect(screen.getByText(/database is busy/)).toBeInTheDocument();
    expect(screen.getByText("database is locked")).toBeInTheDocument();
  });

  test("is disabled when nothing is pending", async () => {
    mapApi("approved");
    renderApp("/maps/id0000000001");
    await screen.findAllByText("Fix 1");
    await waitFor(() => expect(screen.getByRole("button", { name: "Approve all" })).toBeDisabled());
  });
});
