import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { NotAnalysed, NOT_ANALYSED_TIP } from "../src/components/NotAnalysed";

describe("not analysed state", () => {
  test("shows the label with its tooltip when the scan was unanalysed", () => {
    render(<NotAnalysed show />);
    const el = screen.getByRole("status");
    expect(el.textContent).toBe("Not analysed");
    expect(el.getAttribute("title")).toBe(NOT_ANALYSED_TIP);
    expect(NOT_ANALYSED_TIP).toBe("Audio analysis was unavailable; rescan pending");
  });

  test("renders nothing otherwise", () => {
    const { container } = render(<NotAnalysed show={false} />);
    expect(container.innerHTML).toBe("");
  });
});
