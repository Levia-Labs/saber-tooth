import { useHoldRepeat } from "../lib/useHoldRepeat";
import { Icon } from "./icons";

interface ButtonProps {
  label: string;
  up: boolean;
  onStep: (fast: boolean) => void;
}

function StepButton({ label, up, onStep }: ButtonProps) {
  const hold = useHoldRepeat(onStep);
  return (
    <button type="button" className="step-btn" tabIndex={-1} aria-label={label} {...hold}>
      <Icon name={up ? "sort-asc" : "chevron"} />
    </button>
  );
}

interface Props {
  /** Accessible tail, e.g. "minimum BPM". */
  noun: string;
  /** `direction` is 1 for up and -1 for down. */
  onStep: (direction: 1 | -1, fast: boolean) => void;
}

/** A small column of an up and a down arrow beside a number input; holding a button repeats. */
export function StepButtons({ noun, onStep }: Props) {
  return (
    <span className="steps">
      <StepButton label={`Increase ${noun}`} up onStep={(fast) => onStep(1, fast)} />
      <StepButton label={`Decrease ${noun}`} up={false} onStep={(fast) => onStep(-1, fast)} />
    </span>
  );
}
