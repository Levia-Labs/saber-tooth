import { Icon, type IconName } from "../components/icons";
import { useVrMode } from "./VrMode";

const CHOICES = [
  { mode: "vr", label: "VR", icon: "headset" },
  { mode: "desktop", label: "Desktop", icon: "monitor" },
] as const satisfies readonly { mode: string; label: string; icon: IconName }[];

/** VR / Desktop toggle for the masthead: two buttons, not links, so the header keeps no nav. */
export function ModeSwitch() {
  const { mode, choose } = useVrMode();
  return (
    <div className="mode-pick" role="group" aria-label="Layout">
      {CHOICES.map((c) => (
        <button
          key={c.mode}
          type="button"
          className="mode-pick-btn"
          aria-pressed={mode === c.mode}
          onClick={() => choose(c.mode)}
        >
          <Icon name={c.icon} />
          {c.label}
        </button>
      ))}
    </div>
  );
}
