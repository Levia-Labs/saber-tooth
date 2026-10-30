import type { DepState, ModStatus } from "../../api/settings";
import { Spinner } from "../Spinner";

const DEP_LABEL: Record<DepState, string> = {
  current: "Installed",
  other: "Other version kept",
  missing: "Missing",
};

function headline(mod: ModStatus["mod"]): string {
  if (mod.state === "current") return `Installed ${mod.installed_version ?? ""}`.trim();
  if (mod.state === "other") return "Installed, other version";
  if (mod.state === "unsupported") return "Not available for this game version";
  return "Not installed";
}

/** What is installed, what is available and the dependencies, once the mod list has arrived. */
export function ModStatusView({ status }: { status: ModStatus }) {
  const { mod, game, catalog } = status;
  if (catalog.state === "loading") return <Spinner label="Checking BeatMods" />;
  if (catalog.state !== "ready" && catalog.state !== "unsupported") return null;
  const deps = mod.dependencies ?? [];
  return (
    <div className="settings-mod">
      <p className="settings-line">
        <span>Beat Saber {game.version}</span>
        <span className="settings-chip" data-state={mod.state}>
          {headline(mod)}
        </span>
        {mod.available_version && (
          <span className="settings-muted">Available {mod.available_version}</span>
        )}
      </p>
      {deps.length > 0 && (
        <ul className="settings-deps" aria-label="Dependencies">
          {deps.map((d) => (
            <li key={d.name}>
              <span>{d.name}</span>
              <span className="settings-muted">{d.version}</span>
              <span className="settings-chip" data-state={d.state}>
                {DEP_LABEL[d.state]}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
