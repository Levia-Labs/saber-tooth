import { PageShell } from "../components/PageShell";
import { ModsCard } from "../components/settings/ModsCard";
import { ServiceCard } from "../components/settings/ServiceCard";
import { useDocumentTitle } from "../lib/hooks";

export function SettingsPage() {
  useDocumentTitle("Settings");
  return (
    <PageShell
      active="settings"
      title="Settings"
      sectionClass="about-page"
      scroll="Settings content"
    >
      <div className="about settings">
        <h2>Service and mods</h2>
        <div className="settings-grid">
          <ServiceCard />
          <ModsCard />
        </div>
      </div>
    </PageShell>
  );
}
