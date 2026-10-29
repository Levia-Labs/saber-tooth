import * as Dialog from "@radix-ui/react-dialog";
import { useId, useState, type ReactNode } from "react";
import type { Facets } from "../api/types";
import { formatEnvironment } from "../lib/environment";
import { LEVELS } from "../lib/levels";
import { STATUS_META } from "../lib/status";
import { durationInput } from "../lib/range";
import { filterCounts, RANGES, totalFilters, type LibraryState } from "../lib/urlstate";
import {
  EnvFilterBody,
  LevelsFilterBody,
  MapperListBody,
  StatusFilterBody,
  TextFilterBody,
} from "./FilterBodies";
import { Icon } from "./icons";
import { RangeFilterBody } from "./RangeFilterBody";
import { Tip } from "./Tip";

interface Props {
  state: LibraryState;
  facets: Facets | undefined;
  update: (patch: Partial<LibraryState>, replace?: boolean) => void;
  clear: () => void;
  /** Live number of maps matching the current filters; shown on the Show button. */
  matchCount?: number;
}

/** Up to two short names ("Ea, No"); a count when more are chosen; nothing when none. */
export function summarize(names: string[]): string {
  if (!names.length) return "";
  return names.length <= 2 ? names.map((n) => n.slice(0, 2)).join(", ") : String(names.length);
}

/** "1:30-3:00", "1:30+" or "-3:00"; nothing when no bound is set. */
export function rangeSummary(
  low: number | null,
  high: number | null,
  fmt: (n: number) => string,
): string {
  if (low === null && high === null) return "";
  if (high === null) return `${fmt(low as number)}+`;
  return low === null ? `-${fmt(high)}` : `${fmt(low)}-${fmt(high)}`;
}

interface GroupProps {
  title: string;
  summary: string;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}

/** One collapsible filter column: a header row with the column name and a summary badge. */
function Group({ title, summary, open, onToggle, children }: GroupProps) {
  const body = useId();
  return (
    <section className="acc">
      <h3>
        <button
          type="button"
          className="acc-head"
          aria-expanded={open}
          aria-controls={body}
          onClick={onToggle}
        >
          <span className="acc-title">{title}</span>
          {summary && <span className="filter-badge static">{summary}</span>}
          <Icon name="chevron" className={open ? "acc-chev open" : "acc-chev"} />
        </button>
      </h3>
      <div id={body} className="acc-body" hidden={!open}>
        {children}
      </div>
    </section>
  );
}

/** One Filters button that opens the column filters as a fullscreen sheet. */
export function MobileFilters({ state, facets, update, clear, matchCount }: Props) {
  const counts = filterCounts(state);
  const total = totalFilters(counts);
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const flip = (key: string) => setOpen((o) => ({ ...o, [key]: !o[key] }));
  const group = (key: string, title: string, summary: string, children: ReactNode) => (
    <Group title={title} summary={summary} open={!!open[key]} onToggle={() => flip(key)}>
      {children}
    </Group>
  );
  const levelNames = LEVELS.filter((l) => (state.level as string[]).includes(l.key)).map(
    (l) => l.abbr,
  );
  return (
    <Dialog.Root>
      <Tip text="Filter the library by title, author, levels, length, BPM, environment and status.">
        <Dialog.Trigger className="btn plain filters-btn">
          <Icon name="filter" filled={total > 0} />
          <span className="label-hide-mobile">Filters</span>
          {total > 0 && <span className="filter-badge static">{total}</span>}
        </Dialog.Trigger>
      </Tip>
      <Dialog.Portal>
        <Dialog.Content
          className="sheet"
          aria-describedby={undefined}
          onOpenAutoFocus={(e) => {
            // Focus the sheet itself: a tooltip on the first button would swallow Escape.
            e.preventDefault();
            (e.currentTarget as HTMLElement).focus();
          }}
        >
          <div className="sheet-head">
            <Dialog.Title>Filters</Dialog.Title>
            <div className="sheet-tools">
              <Tip text="Clear all filters">
                <button
                  type="button"
                  className="btn icon tap"
                  aria-label="Clear all"
                  disabled={!total}
                  onClick={clear}
                >
                  <Icon name="filter-x" />
                </button>
              </Tip>
              <Tip text="Close filters">
                <Dialog.Close className="btn icon tap" aria-label="Close filters">
                  <Icon name="reject" />
                </Dialog.Close>
              </Tip>
            </div>
          </div>
          <div className="sheet-body">
            {group(
              "title",
              "Title",
              counts.title ? "1" : "",
              <TextFilterBody
                label="Title contains"
                placeholder="Title"
                q={state.qField === "title" ? state.q : ""}
                onChange={(q, replace) => update({ q, qField: "title" }, replace)}
              />,
            )}
            {group(
              "author",
              "Author",
              counts.author ? String(counts.author) : "",
              <>
                <MapperListBody
                  selected={state.mapper}
                  facets={facets}
                  onChange={(mapper) => update({ mapper })}
                />
              </>,
            )}
            {group(
              "levels",
              "Levels",
              summarize(levelNames),
              <LevelsFilterBody
                selected={state.level}
                mode={state.levelMode}
                facets={facets}
                onChange={(patch) => update(patch)}
              />,
            )}
            {group(
              "length",
              "Length",
              rangeSummary(state.durationMin, state.durationMax, durationInput),
              <RangeFilterBody
                name="Length"
                kind="duration"
                min={state.durationMin}
                max={state.durationMax}
                bounds={facets?.duration}
                limit={RANGES.durationMax.max}
                onChange={(r, replace) =>
                  update(
                    {
                      ...("min" in r && { durationMin: r.min }),
                      ...("max" in r && { durationMax: r.max }),
                    },
                    replace,
                  )
                }
              />,
            )}
            {group(
              "bpm",
              "BPM",
              rangeSummary(state.bpmMin, state.bpmMax, String),
              <RangeFilterBody
                name="BPM"
                kind="number"
                min={state.bpmMin}
                max={state.bpmMax}
                bounds={facets?.bpm}
                limit={RANGES.bpmMax.max}
                onChange={(r, replace) =>
                  update(
                    {
                      ...("min" in r && { bpmMin: r.min }),
                      ...("max" in r && { bpmMax: r.max }),
                    },
                    replace,
                  )
                }
              />,
            )}
            {group(
              "env",
              "Env",
              summarize(state.env.map(formatEnvironment)),
              <EnvFilterBody
                selected={state.env}
                facets={facets}
                onChange={(env) => update({ env })}
              />,
            )}
            {group(
              "status",
              "Status",
              summarize(state.status.map((s) => STATUS_META[s].label)),
              <StatusFilterBody
                selected={state.status}
                facets={facets}
                onChange={(status) => update({ status })}
              />,
            )}
          </div>
          <div className="sheet-foot">
            <Dialog.Close className="btn primary show-btn">
              {matchCount === undefined ? "Show" : `Show ${matchCount}`}
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
