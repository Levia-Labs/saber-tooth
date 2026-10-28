import { useBsSearch } from "../api/beatsaver";
import { BsResults } from "../components/beatsaver/BsResults";
import { BarSlotProvider } from "../components/BarSlot";
import { BsTabs } from "../components/beatsaver/BsTabs";
import { bsSiteUrl } from "../lib/bsfilters";
import { useDocumentTitle } from "../lib/hooks";
import { useBsState } from "../lib/useBsState";

export function BeatSaverPage() {
  useDocumentTitle("BeatSaver");
  const controls = useBsState();
  const query = useBsSearch(controls.state);
  return (
    <section className="library" aria-labelledby="bs-heading">
      <BarSlotProvider>
        <BsTabs heading="BeatSaver" headingId="bs-heading" siteUrl={bsSiteUrl(controls.state)} />
        <BsResults query={query} controls={controls} />
      </BarSlotProvider>
    </section>
  );
}
