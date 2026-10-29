import * as Tooltip from "@radix-ui/react-tooltip";
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { ActionButton } from "../src/components/Buttons";
import { Icon } from "../src/components/icons";
import { Spinner } from "../src/components/Spinner";

describe("Spinner", () => {
  test("is an animated status with an accessible name and no visible text", () => {
    const { container } = render(<Spinner label="Loading playlists" />);
    const el = screen.getByRole("status", { name: "Loading playlists" });
    expect(el.querySelector("svg.alert-spin")).not.toBeNull();
    expect(container.textContent).toBe("");
  });

  // A spinner icon passed as a plain icon name (action buttons, status chips) was left static.
  test("every spinner icon animates, wherever it is rendered", () => {
    const { container } = render(
      <Tooltip.Provider>
        <Icon name="spinner" />
        <ActionButton
          icon="spinner"
          label="Cancelling job"
          tip="Waiting for the job to stop"
          onClick={() => {}}
        />
      </Tooltip.Provider>,
    );
    const spinners = container.querySelectorAll("svg");
    expect(spinners).toHaveLength(2);
    spinners.forEach((svg) => expect(svg.classList.contains("alert-spin")).toBe(true));
  });
});
