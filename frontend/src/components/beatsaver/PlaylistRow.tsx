import { Link, useLocation } from "react-router";
import type { BsPlaylist } from "../../api/beatsaver";
import { bsPlaylistHref } from "../../lib/backlink";
import { formatCount, plural } from "../../lib/format";
import { formatNpsRange, formatTotalLength } from "../../lib/plfilters";
import { PL_TIPS } from "../../lib/pltips";
import { ActionButton, ActionLink } from "../Buttons";
import { Cover } from "../Chips";
import { Icon } from "../icons";
import { Tip } from "../Tip";

interface Props {
  playlist: BsPlaylist;
  index: number;
  /** A download job or a map fetch is running: Download all waits. */
  busy: boolean;
  onDownloadAll: (playlist: BsPlaylist) => void;
}

export function PlaylistRow({ playlist: p, index, busy, onDownloadAll }: Props) {
  const { search } = useLocation();
  const to = bsPlaylistHref(p.id, search);
  const site = `https://beatsaver.com/playlists/${encodeURIComponent(p.id)}`;
  const votes = `${p.upvotes} up, ${p.downvotes} down`;
  const percent = Math.round(p.rating * 100);
  return (
    <div className="lib-row lib-grid" role="row" aria-rowindex={index + 2} data-playlist={p.id}>
      <div className="col-cover" role="cell">
        <Cover url={p.cover_url} />
      </div>
      <div className="col-title" role="cell">
        <Tip text={PL_TIPS.open}>
          <Link className="title-link bs-title" to={to} title={p.name}>
            {p.name}
          </Link>
        </Tip>
      </div>
      <div className="col-sub" role="cell">
        <div className="sub">
          <span>{p.owner}</span>
          <span className="sub-tempo">
            {" "}
            &middot; {plural(p.map_count, "map")} &middot; {formatTotalLength(p.duration)}
          </span>
        </div>
      </div>
      <div className="col-author" role="cell" title={p.owner}>
        {p.owner}
      </div>
      <div className="col-maps num" role="cell">
        {p.map_count}
      </div>
      <div className="col-rating num" role="cell">
        <Tip text={`Rated ${percent} percent: ${votes}.`}>
          <span className="bs-rating">{percent}%</span>
        </Tip>
      </div>
      <div className="col-upvotes num" role="cell">
        <Tip text={votes}>
          <span className="bs-ups">
            <Icon name="thumb-up" />
            <span>{formatCount(p.upvotes)}</span>
          </span>
        </Tip>
      </div>
      <div className="col-length num" role="cell">
        {formatTotalLength(p.duration)}
      </div>
      <div className="col-nps num" role="cell">
        {formatNpsRange(p.min_nps, p.max_nps)}
      </div>
      <div className="col-created num" role="cell">
        {p.created_at.slice(0, 10) || "–"}
      </div>
      <div className="col-actions" role="cell">
        <div className="actions">
          <ActionLink
            icon="maps"
            label={`Open ${p.name} in Saber Tooth`}
            tip={PL_TIPS.open}
            to={to}
          />
          <ActionButton
            icon="download"
            label={`Download all maps of ${p.name}`}
            tip={PL_TIPS.downloadAll}
            disabled={busy}
            onClick={() => onDownloadAll(p)}
          />
          <Tip text={PL_TIPS.openSite}>
            <a className="btn icon" href={site} target="_blank" rel="noopener noreferrer">
              <Icon name="external" />
              <span className="sr">{`Open ${p.name} on BeatSaver (new tab)`}</span>
            </a>
          </Tip>
        </div>
      </div>
    </div>
  );
}
