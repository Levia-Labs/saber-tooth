import type { Stage } from "../../lib/genstages";
import { Icon } from "../icons";

/** The generate stages in order: done, the current one, then those still to come. */
export function StageList({ stages }: { stages: Stage[] }) {
  return (
    <ol className="gen-stages">
      {stages.map((stage) => (
        <li
          key={stage.label}
          className={stage.state}
          aria-current={stage.state === "now" ? "step" : undefined}
        >
          {stage.state === "done" && <Icon name="ok" />}
          {stage.label}
        </li>
      ))}
    </ol>
  );
}
