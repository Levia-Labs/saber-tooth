import { useGenerate } from "../api/generate";
import { AddCard } from "../components/generate/AddCard";
import { AnalyseCard } from "../components/generate/AnalyseCard";
import { PageShell } from "../components/PageShell";
import { useDocumentTitle } from "../lib/hooks";

/** Add card (link or audio file) beside the analyse card that follows the generate job. */
export function NewPage() {
  useDocumentTitle("Generate map");
  const gen = useGenerate();
  return (
    <PageShell
      active="library"
      title="Generate map"
      sectionClass="about-page"
      scroll="Generate map"
    >
      <div className="about gen-page">
        <div className="gen-grid">
          <AddCard busy={gen.busy} onRun={(l, s, st) => void gen.run(l, s, st)} />
          {gen.view && <AnalyseCard view={gen.view} />}
        </div>
      </div>
    </PageShell>
  );
}
