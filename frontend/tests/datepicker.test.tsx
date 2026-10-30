import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, test } from "vitest";
import { DatePicker } from "../src/components/DatePicker";
import { addMonths, monthWeeks, parseIso, toIso } from "../src/lib/calendar";

function Harness({
  min,
  max,
  start = "2024-05-15",
}: {
  min?: string;
  max?: string;
  start?: string;
}) {
  const [v, setV] = useState(start);
  return (
    <>
      <DatePicker
        id="d"
        label="From"
        value={v}
        onChange={setV}
        min={min}
        max={max}
        locale="en-US"
      />
      <output data-testid="v">{v}</output>
    </>
  );
}

const open = async () => {
  await userEvent.click(screen.getByRole("button", { name: /^From/ }));
  return screen.findByRole("dialog", { name: "From calendar" });
};
const value = () => screen.getByTestId("v").textContent;

describe("calendar helpers", () => {
  test("round trip and clamping", () => {
    expect(toIso(parseIso("2024-02-29")!)).toBe("2024-02-29");
    expect(parseIso("2023-02-29")).toBeNull();
    expect(toIso(addMonths(parseIso("2024-01-31")!, 1))).toBe("2024-02-29");
    expect(monthWeeks(parseIso("2024-05-15")!, 0).every((w) => w.length === 7)).toBe(true);
  });
});

describe("DatePicker", () => {
  test("opens on the selected day and arrow keys move focus", async () => {
    render(<Harness />);
    const dialog = await open();
    expect(within(dialog).getByRole("grid")).toBeInTheDocument();
    const day = await within(dialog).findByRole("button", { name: /May 15, 2024/ });
    expect(day).toHaveFocus();
    await userEvent.keyboard("{ArrowRight}");
    expect(within(dialog).getByRole("button", { name: /May 16, 2024/ })).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(within(dialog).getByRole("button", { name: /May 23, 2024/ })).toHaveFocus();
    await userEvent.keyboard("{PageDown}");
    expect(within(dialog).getByRole("button", { name: /June 23, 2024/ })).toHaveFocus();
    await userEvent.keyboard("{End}");
    expect(within(dialog).getByRole("button", { name: /June 29, 2024/ })).toHaveFocus();
    await userEvent.keyboard("{Home}");
    expect(within(dialog).getByRole("button", { name: /June 23, 2024/ })).toHaveFocus();
  });

  test("Enter selects the focused day and closes", async () => {
    render(<Harness />);
    await open();
    await userEvent.keyboard("{ArrowRight}{Enter}");
    expect(value()).toBe("2024-05-16");
    expect(screen.queryByRole("dialog", { name: "From calendar" })).toBeNull();
  });

  test("Escape closes without changing the value", async () => {
    render(<Harness />);
    await open();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "From calendar" })).toBeNull();
    expect(value()).toBe("2024-05-15");
  });

  test("min and max disable days and clamp keyboard movement", async () => {
    render(<Harness min="2024-05-10" max="2024-05-20" />);
    const dialog = await open();
    expect(within(dialog).getByRole("button", { name: /May 9, 2024/ })).toBeDisabled();
    expect(within(dialog).getByRole("button", { name: /May 21, 2024/ })).toBeDisabled();
    await userEvent.keyboard("{PageDown}");
    expect(within(dialog).getByRole("button", { name: /May 20, 2024/ })).toHaveFocus();
  });

  test("Clear empties the value and Today picks today", async () => {
    render(<Harness />);
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(value()).toBe("");
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Today" }));
    expect(value()).toBe(toIso(new Date()));
  });

  test("the year select jumps years", async () => {
    render(<Harness />);
    const dialog = await open();
    await userEvent.selectOptions(within(dialog).getByLabelText("Year"), "2022");
    expect(within(dialog).getByRole("grid", { name: "May 2022" })).toBeInTheDocument();
  });
});
