import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { MapTitle } from "../src/components/MapTitle";

const setup = (onSave = vi.fn().mockResolvedValue(undefined)) => {
  render(<MapTitle name="Old" onSave={onSave} />);
  return onSave;
};

describe("MapTitle", () => {
  test("clicking the title opens an input; Enter saves the trimmed name", async () => {
    const onSave = setup();
    await userEvent.click(screen.getByRole("button", { name: "Rename map: Old" }));
    const input = screen.getByRole("textbox", { name: "Map name" });
    await userEvent.clear(input);
    await userEvent.type(input, "  New  {Enter}");
    expect(onSave).toHaveBeenCalledWith("New");
    await waitFor(() => expect(screen.queryByRole("textbox")).toBeNull());
  });

  test("the pencil button opens the input", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: "Edit map name" }));
    expect(screen.getByRole("textbox", { name: "Map name" })).toBeTruthy();
  });

  test("Escape cancels without saving, also when the input then blurs", async () => {
    const onSave = setup();
    await userEvent.click(screen.getByRole("button", { name: "Edit map name" }));
    await userEvent.type(screen.getByRole("textbox"), "x{Escape}");
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  test("blur saves", async () => {
    const onSave = setup();
    await userEvent.click(screen.getByRole("button", { name: "Edit map name" }));
    await userEvent.type(screen.getByRole("textbox"), "2");
    await userEvent.tab();
    await waitFor(() => expect(onSave).toHaveBeenCalledWith("Old2"));
  });

  test("an unchanged name closes without a request", async () => {
    const onSave = setup();
    await userEvent.click(screen.getByRole("button", { name: "Edit map name" }));
    await userEvent.type(screen.getByRole("textbox"), "{Enter}");
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  test("a path separator is refused inline", async () => {
    const onSave = setup();
    await userEvent.click(screen.getByRole("button", { name: "Edit map name" }));
    await userEvent.type(screen.getByRole("textbox"), "/{Enter}");
    expect((await screen.findByRole("alert")).textContent).toMatch(/cannot contain/);
    expect(onSave).not.toHaveBeenCalled();
  });

  test("a failed save shows the error and keeps the input", async () => {
    setup(vi.fn().mockRejectedValue(new Error("a folder named X already exists")));
    await userEvent.click(screen.getByRole("button", { name: "Edit map name" }));
    await userEvent.type(screen.getByRole("textbox"), "X{Enter}");
    expect((await screen.findByRole("alert")).textContent).toMatch(/already exists/);
    expect(screen.getByRole("textbox")).toBeTruthy();
  });
});
