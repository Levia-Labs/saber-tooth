import { SectionTabs } from "../components/SectionTabs";
import { ModsCard } from "../components/settings/ModsCard";
import { ServiceCard } from "../components/settings/ServiceCard";
import { useDocumentTitle } from "../lib/hooks";

export function SettingsPage() {
  useDocumentTitle("Settings");
  return (
    <section className="library about-page" aria-labelledby="settings-heading">
      <div className="lib-bar">
        <div className="lib-title">
          <SectionTabs active="settings" heading="Settings" headingId="settings-heading" />
        </div>
      </div>
      <div
        className="lib-scroll about-scroll"
        role="region"
        aria-label="Settings content"
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- a scroll region must take focus so the keyboard can scroll it
        tabIndex={0}
      >
        <div className="about settings">
          <h2>Service and mods</h2>
          <div className="settings-grid">
            <ServiceCard />
            <ModsCard />
          </div>
        </div>
      </div>
    </section>
  );
}
