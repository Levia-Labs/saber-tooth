import * as Checkbox from "@radix-ui/react-checkbox";
import type { BsMap } from "../../api/beatsaver";
import { BS_TIPS } from "../../lib/bstips";
import { formatBpm, formatDuration } from "../../lib/format";
import { ActionButton } from "../Buttons";
import { Cover, LevelChips } from "../Chips";
import { Icon } from "../icons";
import { Tip } from "../Tip";
import type { RowStatus } from "./downloads";
import { PreviewButton } from "./Preview";

interface Props {
  item: BsMap;
  index: number;
  selected: boolean;
  status: RowStatus;
  onSelect: (item: BsMap) => void;
  onDownload: (id: string) => void;
}

const MAX_TAGS = 3;

function levelsOf(item: BsMap) {
  const names = item.difficulties.map((d) => d.difficulty);
  const nps = Object.fromEntries(item.difficulties.map((d) => [d.difficulty, d.nps]));
  return { names, nps };
}

function Tags({ tags }: { tags: string[] }) {
  if (!tags.length) return null;
  const shown = tags.slice(0, MAX_TAGS);
  const rest = tags.slice(MAX_TAGS);
  return (
    <ul className="bs-tags" aria-label="Tags">
      {shown.map((t) => (
        <li key={t} className="bs-tag">
          {t}
        </li>
      ))}
      {rest.length > 0 && (
        <li className="bs-tag more">
          <Tip text={rest.join(", ")}>
            <span>+{rest.length}</span>
          </Tip>
        </li>
      )}
    </ul>
  );
}

export function BsStatusChip({ status }: { status: RowStatus }) {
  if (status.kind === "none") return null;
  const meta = {
    installed: { cls: "ok", icon: "ok", text: "Installed", tip: BS_TIPS.installed },
    downloading: {
      cls: "scanning",
      icon: "spinner",
      text: "Downloading",
      tip: BS_TIPS.downloading,
    },
    failed: { cls: "error", icon: "error", text: "Failed", tip: "" },
  } as const;
  const m = meta[status.kind];
  const tip = status.kind === "failed" ? `${BS_TIPS.failed} ${status.reason}` : m.tip;
  return (
    <Tip text={tip}>
      <span className={`chip chip-${m.cls}`} data-status={status.kind} role="img" aria-label={tip}>
        <Icon name={m.icon} />
        <span className="chip-text" aria-hidden="true">
          {m.text}
        </span>
      </span>
    </Tip>
  );
}

export function BsRow({ item, index, selected, status, onSelect, onDownload }: Props) {
  const name = item.song || item.name;
  const { names, nps } = levelsOf(item);
  const href = `https://beatsaver.com/maps/${encodeURIComponent(item.id)}`;
  const blocked = status.kind === "installed" || status.kind === "downloading";
  const votes = `${item.upvotes} up, ${item.downvotes} down`;
  return (
    <div className="lib-row lib-grid" role="row" aria-rowindex={index + 2} data-map={item.id}>
      <div className="col-select" role="cell">
        <Checkbox.Root
          className="checkbox"
          checked={selected}
          aria-label={`Select ${name}`}
          onCheckedChange={() => onSelect(item)}
        >
          <Checkbox.Indicator>
            <Icon name="approve" />
          </Checkbox.Indicator>
        </Checkbox.Root>
      </div>
      <div className="col-cover" role="cell">
        <Cover url={item.cover_url} />
      </div>
      <div className="col-title" role="cell">
        <span className="bs-title" title={name}>
          {name}
        </span>
      </div>
      <div className="col-sub" role="cell">
        <div className="sub">
          <span>{item.mapper}</span>
          <span className="sub-tempo">
            {" "}
            &middot; {formatDuration(item.duration)} &middot; {formatBpm(item.bpm)}
          </span>
        </div>
        <LevelChips names={names} nps={nps} className="levels-inline" />
      </div>
      <div className="col-author" role="cell" title={item.mapper}>
        {item.mapper}
      </div>
      <div className="col-levels" role="cell">
        <LevelChips names={names} nps={nps} />
      </div>
      <div className="col-rating num" role="cell">
        <Tip text={`Rated ${Math.round(item.rating * 100)} percent: ${votes}.`}>
          <span className="bs-rating">
            <strong>{Math.round(item.rating * 100)}%</strong>
            <span className="bs-votes">
              {item.upvotes} / {item.downvotes}
            </span>
          </span>
        </Tip>
      </div>
      <div className="col-tempo num" role="cell">
        <span>{formatDuration(item.duration)}</span>
        <span className="bs-votes">{formatBpm(item.bpm)}</span>
      </div>
      <div className="col-tags" role="cell">
        <Tags tags={item.tags} />
      </div>
      <div className="col-status" role="cell">
        <BsStatusChip status={status} />
      </div>
      <div className="col-actions" role="cell">
        <div className="actions">
          <ActionButton
            icon="download"
            label={`Download ${name}`}
            short="Download"
            tip={status.kind === "installed" ? BS_TIPS.downloadInstalled : BS_TIPS.download}
            disabled={blocked}
            onClick={() => onDownload(item.id)}
          />
          {item.preview_url && <PreviewButton url={item.preview_url} name={name} />}
          <Tip text={BS_TIPS.open}>
            <a className="btn icon" href={href} target="_blank" rel="noopener noreferrer">
              <Icon name="external" />
              <span className="sr">{`Open ${name} on BeatSaver (new tab)`}</span>
              <span className="short" aria-hidden="true">
                Open
              </span>
            </a>
          </Tip>
        </div>
      </div>
    </div>
  );
}
