import { exportHint, REFRESH_HINT } from "../../lib/lpfilters";
import { Box } from "../beatsaver/Box";

interface Props {
  author: string;
  description: string;
  folder: string;
  sync: boolean;
  onAuthor: (author: string) => void;
  onDescription: (description: string) => void;
  onFolder: (folder: string) => void;
  onSync: (sync: boolean) => void;
}

/** Export settings: the subfolder of the playlists folder and the sync URL switch. */
export function LpExport(p: Props) {
  const { folder, sync, onFolder, onSync } = p;
  return (
    <section className="lp-export" aria-label="Export settings">
      <div className="lp-fields">
        <label>
          Author
          <input
            className="input"
            value={p.author}
            placeholder="saber-tooth"
            onChange={(e) => p.onAuthor(e.target.value)}
          />
        </label>
        <label className="lp-wide">
          Description
          <textarea
            className="input"
            rows={2}
            value={p.description}
            onChange={(e) => p.onDescription(e.target.value)}
          />
        </label>
        <label>
          Subfolder
          <input
            className="input"
            value={folder}
            placeholder="saber-tooth"
            onChange={(e) => onFolder(e.target.value)}
          />
          <span className="lp-sub">Written to {exportHint(folder)}</span>
        </label>
        <Box id="lp-sync" checked={sync} onToggle={() => onSync(!sync)}>
          Keep in sync (PlaylistManager refreshes it from this server)
        </Box>
      </div>
      <p className="lp-hint" role="note">
        {REFRESH_HINT}
      </p>
    </section>
  );
}
