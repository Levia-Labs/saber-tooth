import { Icon, type IconName } from "../components/icons";
import { Logo } from "../components/Logo";
import { SectionTabs } from "../components/SectionTabs";
import { useDocumentTitle } from "../lib/hooks";

const LINKS = [
  { href: "https://github.com/Levia-Labs/saber-tooth", label: "Saber Tooth on GitHub" },
  { href: "https://levialabs.net", label: "Levia Labs" },
  { href: "https://github.com/Levia-Labs/beat-analyser", label: "beat-analyser (companion)" },
  { href: "https://github.com/Levia-Labs/Crepidoma", label: "Crepidoma (companion)" },
];

interface Feature {
  icon: IconName;
  title: string;
  text: string;
}

const FEATURES: Feature[] = [
  {
    icon: "scan",
    title: "Quality checker",
    text: "Scan finds impossible swings, broken parity and empty stretches. Fixes are proposed on a timeline, and each one is verified to reach zero findings before it is offered.",
  },
  {
    icon: "fix",
    title: "One-click Fix",
    text: 'Adds the missing Standard difficulties (Easy to Expert+) and fixes every finding it can, then writes a new "[saber-tooth]" folder next to the original. The original map is never changed, and it is hidden from the library once fixed.',
  },
  {
    icon: "generate",
    title: "Generate from a song",
    text: "Give it a YouTube link or drop an audio file. The beat-analyser companion finds the beat grid, and the map is written, fixed, straight into CustomLevels.",
  },
  {
    icon: "learn",
    title: "Lightshows",
    text: "Lighting follows the energy and structure of the song, from a bundled learned set. Learn lightshows adds the styles of the maps you have installed.",
  },
  {
    icon: "scissors",
    title: "Crop",
    text: "Cut a highlight of 1 minute, 2 minutes or any length down to 1 second on an NPS chart with sections and playback. Save it as a new map or over the original.",
  },
  {
    icon: "search",
    title: "BeatSaver",
    text: "Search with filters BeatSaver itself lacks, such as maps that have Easy, Normal and Hard. Save presets, browse playlists and download maps into your library.",
  },
  {
    icon: "clock",
    title: "Jobs",
    text: "See what the server is running, what waits and what finished in the last day. Cancel running or queued jobs and retry failed ones. Queued jobs survive a restart.",
  },
  {
    icon: "maps",
    title: "VR mode",
    text: "The same pages scaled up for a headset browser, with a Layout switch in the header. A helper on the host detects the headset runtime.",
  },
  {
    icon: "external",
    title: "MCP tools",
    text: "Agents can scan, approve, apply, generate, crop and search BeatSaver over MCP at /mcp, using the same jobs as the interface.",
  },
];

const STEPS = [
  "Open the Library and pick a map.",
  "Press Fix, or Scan to review each proposal on the map page first.",
  "Play the “[saber-tooth]” copy in Beat Saber.",
  "Use the Crop tab for a shorter version, or Generate map for a new one from a song.",
  "Watch progress in Jobs; results also appear as toasts at the bottom.",
];

export function AboutPage() {
  useDocumentTitle("About");
  return (
    <section className="library about-page" aria-labelledby="about-heading">
      <div className="lib-bar">
        <div className="lib-title">
          <SectionTabs active="about" heading="About Saber Tooth" headingId="about-heading" />
        </div>
      </div>
      <div
        className="lib-scroll about-scroll"
        role="region"
        aria-label="About content"
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- a scroll region must take focus so the keyboard can scroll it
        tabIndex={0}
      >
        <div className="about">
          <header className="about-hero">
            <Logo size={72} />
            <div>
              <p className="about-name">Saber Tooth</p>
              <p className="about-lead">
                A local tool that makes Beat Saber custom maps playable. One Fix click adds missing
                difficulties and repairs impossible or uncomfortable patterns, then saves a new copy
                next to the original.
              </p>
              <ul className="about-badges" aria-label="Highlights">
                <li>Runs on your computer</li>
                <li>Original maps untouched</li>
                <li>Vanilla features only</li>
              </ul>
            </div>
          </header>

          <h2>What it does</h2>
          <ul className="about-grid" aria-label="Features">
            {FEATURES.map((f) => (
              <li key={f.title} className="about-card">
                <div className="about-card-head">
                  <span className="about-icon">
                    <Icon name={f.icon} />
                  </span>
                  <h3>{f.title}</h3>
                </div>
                <p>{f.text}</p>
              </li>
            ))}
          </ul>

          <h2>How to use it</h2>
          <ol className="about-steps" aria-label="How to use it">
            {STEPS.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>

          <h2>Good to know</h2>
          <ul className="about-notes">
            <li>
              <strong>Vanilla only.</strong> Chroma, Noodle Extensions or Vivify are never required;
              lighting uses the vanilla environments.
            </li>
            <li>
              <strong>Private.</strong> Saber Tooth only talks to BeatSaver when you search or
              download there, and to the beat-analyser when it needs the audio.
            </li>
            <li>
              <strong>Your maps are safe.</strong> Fix, Apply and Crop write new folders. Only Save
              over this map in Crop and Delete change an existing folder, and both ask first.
            </li>
          </ul>

          <h2>Links</h2>
          <ul className="about-links">
            {LINKS.map((l) => (
              <li key={l.href}>
                <a href={l.href} target="_blank" rel="noopener noreferrer">
                  {l.label}
                </a>
              </li>
            ))}
          </ul>

          <p className="muted about-version">Version {__APP_VERSION__}</p>
        </div>
      </div>
    </section>
  );
}
