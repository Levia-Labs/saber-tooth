import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { applyMap, generateFromFile, generateFromUrl, getProposals } from "../api/client";
import { useJobRunner } from "../api/jobs";
import { keys, retry } from "../api/queries";
import type { Note } from "../api/types";
import { useAnnounce } from "../components/Announcer";
import { ActionButton } from "../components/Buttons";
import { Icon } from "../components/icons";
import { JobOutcome } from "../components/JobOutcome";
import { ProposalCard } from "../components/ProposalCard";
import { libraryHref, useDocumentTitle } from "../lib/hooks";
import { applyTip, TIPS } from "../lib/tips";

const FIRST_16_BARS = 64;
const firstBars = (notes: Note[]): Note[] => notes.filter((n) => n.beat < FIRST_16_BARS);

function Preview({ mapId }: { mapId: string }) {
  const client = useQueryClient();
  const write = useJobRunner("Write map");
  const found = useQuery({
    queryKey: keys.proposals(mapId),
    queryFn: () => getProposals(mapId),
    retry,
  });
  const created = (found.data ?? []).filter((p) => p.rule === "create-map");
  const expert = created.filter((p) => p.difficulty === "Expert");
  const approvedAny = created.some((p) => p.status === "approved");
  return (
    <section aria-label="Proposed map">
      <h2>Proposed map (first 16 bars of Expert)</h2>
      <ul>
        {created.map((p) => (
          <li key={p.id}>
            {p.difficulty}: {p.after.length} notes
          </li>
        ))}
      </ul>
      {expert.map((p) => (
        <ProposalCard key={p.id} proposal={p} mapId={mapId} notesFilter={firstBars} defaultOpen />
      ))}
      <ActionButton
        icon="apply"
        label="Write map folder"
        tip={applyTip("<map>")}
        text
        variant="primary"
        disabled={!approvedAny || write.busy}
        onClick={() =>
          void write
            .run(() => applyMap(mapId))
            .then(() => client.invalidateQueries({ queryKey: keys.proposals(mapId) }))
        }
      />
      <JobOutcome job={write.job} error={write.error} />
    </section>
  );
}

export function NewPage() {
  useDocumentTitle("Generate map");
  const announce = useAnnounce();
  const gen = useJobRunner("Generate");
  const [url, setUrl] = useState("");
  const file = useRef<HTMLInputElement>(null);
  const [mapId, setMapId] = useState<string | null>(null);
  const urlId = useId();
  const fileId = useId();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const chosen = file.current?.files?.[0];
    const text = url.trim();
    if (!chosen && !text) {
      announce("Provide a URL or an audio file.");
      return;
    }
    setMapId(null);
    const job = await gen.run(() => (chosen ? generateFromFile(chosen) : generateFromUrl(text)));
    const id = job?.result?.["map_id"];
    if (job && (typeof id === "string" || typeof id === "number")) setMapId(String(id));
  };

  return (
    <section className="page new-page">
      <Link className="back" to={libraryHref()}>
        <Icon name="back" />
        Library
      </Link>
      <h1 tabIndex={-1} data-page-heading>
        Generate map
      </h1>
      <form className="gen-form" onSubmit={(e) => void submit(e)}>
        <label htmlFor={urlId}>YouTube URL</label>
        <input
          id={urlId}
          type="url"
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <label htmlFor={fileId}>or audio file</label>
        <input id={fileId} ref={file} type="file" accept="audio/*" />
        <ActionButton
          type="submit"
          icon="generate"
          label="Generate"
          tip={TIPS.generate}
          text
          variant="primary"
          disabled={gen.busy}
        />
      </form>
      {gen.error && <JobOutcome job={gen.job} error={gen.error} />}
      {gen.state === "done" && !mapId && <JobOutcome job={gen.job} error={null} />}
      {mapId && <Preview mapId={mapId} />}
    </section>
  );
}
