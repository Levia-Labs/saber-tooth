import { useFix } from "../api/fix";
import type { MapItem } from "../api/types";
import { mapName } from "../lib/status";
import { TIPS } from "../lib/tips";
import { ActionButton } from "./Buttons";

/** The primary action: one click makes the map playable and writes '<map> [saber-tooth]'. */
export function FixButton({ item, text = false }: { item: MapItem; text?: boolean }) {
  const name = mapName(item);
  const fix = useFix(item, name);
  const busy = item.job !== null || item.status === "unreadable";
  return (
    <ActionButton
      icon="fix"
      label={text ? "Fix" : `Fix ${name}`}
      tip={TIPS.fix}
      variant="accent"
      text={text}
      disabled={busy}
      onClick={() => void fix()}
    />
  );
}
