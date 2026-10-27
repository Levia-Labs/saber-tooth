import { useBsSearch } from "../api/beatsaver";
import { BsResults } from "../components/beatsaver/BsResults";
import { BsTabs } from "../components/beatsaver/BsTabs";
import { useDocumentTitle } from "../lib/hooks";
import { useBsState } from "../lib/useBsState";

export function BeatSaverPage() {
  useDocumentTitle("BeatSaver");
  const controls = useBsState();
  const query = useBsSearch(controls.state);
  return (
    <section className="library" aria-labelledby="bs-heading">
      <BsTabs tab="maps" heading="BeatSaver" headingId="bs-heading" />
      <BsResults query={query} controls={controls} />
    </section>
  );
}
