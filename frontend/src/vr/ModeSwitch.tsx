import { useVrMode } from "./VrMode";

const CHOICES = [
  { mode: "vr", label: "VR" },
  { mode: "desktop", label: "Desktop" },
] as const;

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
          {c.label}
        </button>
      ))}
    </div>
  );
}
