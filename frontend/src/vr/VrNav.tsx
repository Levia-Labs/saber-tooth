import { Link } from "react-router";

const ITEMS = [
  { key: "library", to: "/vr", label: "Library" },
  { key: "beatsaver", to: "/vr/beatsaver", label: "BeatSaver" },
] as const;

/** Library | BeatSaver as two large links at the top of each VR list screen. */
export function VrNav({ active }: { active: "library" | "beatsaver" }) {
  return (
    <nav className="vr-nav" aria-label="Section">
      {ITEMS.map((i) => (
        <Link
          key={i.key}
          className="vr-target"
          to={i.to}
          aria-current={i.key === active ? "page" : undefined}
        >
          {i.label}
        </Link>
      ))}
    </nav>
  );
}
