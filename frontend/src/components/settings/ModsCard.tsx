import { useInstallMod, useModStatus, type ModStatus } from "../../api/settings";
import { Alert } from "../Alert";
import { ConfirmDialog } from "../ConfirmDialog";
import { EmptyState } from "../EmptyState";
import { Icon } from "../icons";
import { Spinner } from "../Spinner";
import { CardHead } from "./CardHead";
import { GameFolder } from "./GameFolder";
import { ModStatusView } from "./ModStatusView";

function MountHelp({ help }: { help: NonNullable<ModStatus["mount_help"]> }) {
  return (
    <div className="settings-mount">
      <p>Add the Beat Saber folder to the compose stack:</p>
      <pre>{help.env}</pre>
      <pre>
        {help.compose.map((line) => (
          <code key={line}>{line}</code>
        ))}
      </pre>
      <p>{help.then}</p>
    </div>
  );
}

function InstallRow({ status }: { status: ModStatus }) {
  const install = useInstallMod();
  const running = status.install.state === "running" || install.isPending;
  const { mod, game } = status;
  const title = `Install ${mod.name}?`;
  const description =
    `Close Beat Saber first. This adds ${mod.name}${
      mod.available_version ? ` ${mod.available_version}` : ""
    } ` +
    `and any missing dependencies to Plugins and Libs in ${game.path ?? "the game folder"}. ` +
    "Files that already exist are never overwritten.";
  return (
    <div className="settings-actions">
      <ConfirmDialog
        title={title}
        description={description}
        confirmLabel="Install"
        onConfirm={() => install.mutate()}
      >
        <button type="button" className="btn primary" disabled={!mod.can_install || running}>
          Install
        </button>
      </ConfirmDialog>
      {running && <Spinner label="Installing" />}
      {status.install.state === "running" && status.install.message && (
        <span className="settings-muted">{status.install.message}</span>
      )}
      <a className="btn plain" href={mod.github} target="_blank" rel="noreferrer noopener">
        <Icon name="github" />
        PlaylistManager on GitHub
      </a>
    </div>
  );
}

function Outcome({ status, retry }: { status: ModStatus; retry: () => void }) {
  const { install, catalog, mod, game } = status;
  return (
    <>
      {install.state === "failed" && (
        <Alert variant="danger" title="Install failed" message={install.message ?? undefined} />
      )}
      {install.state === "done" && (
        <Alert variant="success" title="Installed" message={install.message ?? undefined} />
      )}
      {catalog.state === "failed" && (
        <Alert
          variant="warning"
          title="Could not reach BeatMods"
          message={catalog.error ?? undefined}
          actions={
            <button type="button" className="btn" onClick={retry}>
              Try again
            </button>
          }
        />
      )}
      {game.state === "ready" && mod.reason && !mod.can_install && install.state !== "running" && (
        <p className="settings-note">{mod.reason}</p>
      )}
    </>
  );
}

/** The Mods card: PlaylistManager status, versions, install and its GitHub link. */
export function ModsCard() {
  const query = useModStatus();
  const status = query.data;
  return (
    <section className="about-card settings-card" aria-labelledby="settings-mods">
      <CardHead icon="plug" title="Mods" id="settings-mods" />
      <p className="settings-sub">PlaylistManager lets you manage playlists inside Beat Saber.</p>
      {!status && <EmptyState icon="plug" text="" pending="Checking PlaylistManager" />}
      {status?.game.state === "not_mounted" && (
        <>
          <EmptyState
            icon="plug"
            text="The game folder is not mounted."
            hint="Mount your Beat Saber folder, or enter where the service sees it."
          />
          {status.mount_help && <MountHelp help={status.mount_help} />}
        </>
      )}
      {status?.game.state === "ready" && <ModStatusView status={status} />}
      {status && <GameFolder />}
      {status && <InstallRow status={status} />}
      {status && <Outcome status={status} retry={() => void query.refetch()} />}
    </section>
  );
}
