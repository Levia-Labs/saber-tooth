import * as Dialog from "@radix-ui/react-dialog";
import type { Facets } from "../api/types";
import { filterCounts, totalFilters, type LibraryState } from "../lib/urlstate";
import {
  EnvFilterBody,
  LevelsFilterBody,
  MapperListBody,
  StatusFilterBody,
  TextFilterBody,
} from "./FilterBodies";
import { Icon } from "./icons";
import { Tip } from "./Tip";

interface Props {
  state: LibraryState;
  facets: Facets | undefined;
  update: (patch: Partial<LibraryState>, replace?: boolean) => void;
  clear: () => void;
}

/** One Filters button that opens the three column filters as a bottom sheet. */
export function MobileFilters({ state, facets, update, clear }: Props) {
  const counts = filterCounts(state);
  const total = totalFilters(counts);
  return (
    <Dialog.Root>
      <Tip text="Filter the library by title, author, levels, status and environment.">
        <Dialog.Trigger className="btn plain filters-btn">
          <Icon name="filter" filled={total > 0} />
          <span>Filters</span>
          {total > 0 && <span className="filter-badge static">{total}</span>}
        </Dialog.Trigger>
      </Tip>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="sheet" aria-describedby={undefined}>
          <div className="sheet-head">
            <Dialog.Title>Filters</Dialog.Title>
            <button type="button" className="btn plain" disabled={!total} onClick={clear}>
              Clear all
            </button>
          </div>
          <section>
            <h3>Title</h3>
            <TextFilterBody
              label="Title contains"
              q={state.qField === "title" ? state.q : ""}
              onChange={(q, replace) => update({ q, qField: "title" }, replace)}
            />
          </section>
          <section>
            <h3>Author</h3>
            <TextFilterBody
              label="Name contains"
              q={state.qField === "mapper" ? state.q : ""}
              onChange={(q, replace) => update({ q, qField: "mapper" }, replace)}
            />
            <MapperListBody
              selected={state.mapper}
              facets={facets}
              onChange={(mapper) => update({ mapper })}
            />
          </section>
          <section>
            <h3>Levels</h3>
            <LevelsFilterBody
              selected={state.level}
              mode={state.levelMode}
              facets={facets}
              onChange={(patch) => update(patch)}
            />
          </section>
          <section>
            <h3>Status</h3>
            <StatusFilterBody
              selected={state.status}
              facets={facets}
              onChange={(status) => update({ status })}
            />
          </section>
          <section>
            <h3>Environment</h3>
            <EnvFilterBody
              selected={state.env}
              facets={facets}
              onChange={(env) => update({ env })}
            />
          </section>
          <Dialog.Close className="btn primary">Show maps</Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
