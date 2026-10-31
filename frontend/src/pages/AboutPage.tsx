import { Icon, type IconName } from "../components/icons";
import { Logo } from "../components/Logo";
import { PageShell } from "../components/PageShell";
import { useDocumentTitle } from "../lib/hooks";

interface LinkCard {
  icon: IconName;
  title: string;
  text: string;
  href: string;
}

const REPO = "https://github.com/Levia-Labs/saber-tooth";

const LINKS: LinkCard[] = [
  {
    icon: "github",
    title: "Saber Tooth on GitHub",
    text: "Source code, issues and releases.",
    href: REPO,
  },
  {
    icon: "docker",
    title: "Docker Hub",
    text: "The saber-tooth image to run with Docker.",
    href: "https://hub.docker.com/r/levialabs/sabertooth",
  },
  {
    icon: "book",
    title: "API reference",
    text: "Every REST route, job result and error the service answers.",
    href: `${REPO}/blob/main/docs/api.md`,
  },
  {
    icon: "plug",
    title: "MCP setup",
    text: "Connect an agent to the MCP endpoint and see the tools it gets.",
    href: `${REPO}/blob/main/docs/api.md#mcp`,
  },
  {
    icon: "download",
    title: "BeatSaver",
    text: "The map site that search and downloads talk to.",
    href: "https://beatsaver.com",
  },
  {
    icon: "globe",
    title: "Levia Labs",
    text: "The people behind Saber Tooth.",
    href: "https://levialabs.net",
  },
  {
    icon: "wave",
    title: "beat-analyser (companion)",
    text: "The sidecar that finds the beat grid of a song.",
    href: "https://github.com/Levia-Labs/beat-analyser",
  },
  {
    icon: "layers",
    title: "Crepidoma (companion)",
    text: "The shared directives and tooling this project is built with.",
    href: "https://github.com/Levia-Labs/Crepidoma",
  },
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
    icon: "review",
    title: "Status tab",
    text: "Lists every finding of a map. After a Fix it also says why each finding that is still open was left, so you know what to change by hand.",
  },
  {
    icon: "fix",
    title: "One-click Fix",
    text: 'Adds the missing Standard difficulties (Easy to Expert+) and fixes every finding it can, then writes a new "[saber-tooth]" folder next to the original. The original map is never changed, and it is hidden from the library once fixed.',
  },
  {
    icon: "queue",
    title: "Batched scan and Fix",
    text: "Scan and Fix work through a map in batches and save as they go. After a cancel, a timeout or an error, a retry resumes from the last saved batch.",
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
    icon: "layers",
    title: "Relight",
    text: "Light a map in another vanilla environment. The lightshow is regenerated on the saber-tooth copy and its fixes stay; the original is never changed.",
  },
  {
    icon: "scissors",
    title: "Crop",
    text: "Cut a highlight of 1 minute, 2 minutes or any length down to 1 second on an NPS chart with sections and playback. Auto crop suggests up to three windows. Save it as a new map or over the original.",
  },
  {
    icon: "search",
    title: "BeatSaver",
    text: "Search with filters BeatSaver itself lacks, such as maps that have Easy, Normal and Hard. Save presets, browse playlists and download maps into your library.",
  },
  {
    icon: "playlist",
    title: "Playlists",
    text: "Build local playlists from your maps, with the SongCore hash of each. Export a .bplist, or turn on a sync URL so PlaylistManager refreshes the list on its own.",
  },
  {
    icon: "clock",
    title: "Jobs",
    text: "A table of what the server is running, what waits and what finished in the last day. Cancel running or queued jobs, retry or restart failed ones. Queued jobs survive a restart.",
  },
  {
    icon: "settings",
    title: "Settings",
    text: "Choose how many fix and scan jobs run at once, next to the cores and memory the container has. Check for PlaylistManager and install it from BeatMods in one click.",
  },
  {
    icon: "maps",
    title: "VR and mobile layouts",
    text: "The same pages scaled up for a headset browser, with a Layout switch in the header, and laid out to fit a phone. A helper on the host detects the headset runtime.",
  },
  {
    icon: "external",
    title: "MCP tools",
    text: "Agents can scan, approve, apply, generate, crop and search BeatSaver over MCP at /mcp, using the same jobs as the interface.",
  },
];

const STEPS = [
  { title: "Open the Library", text: "Pick a map from your library." },
  { title: "Press Fix", text: "Or press Scan to review each proposal on the map page first." },
  { title: "Play the copy", text: "Play the “[saber-tooth]” copy in Beat Saber." },
  {
    title: "Crop or generate",
    text: "Use the Crop tab for a shorter version, or Generate map for a new one from a song.",
  },
  {
    title: "Watch Jobs",
    text: "Watch progress in Jobs, where you can cancel or retry; results also appear as toasts at the bottom.",
  },
];

const NOTES: Feature[] = [
  {
    icon: "ok",
    title: "Vanilla only",
    text: "Chroma, Noodle Extensions or Vivify are never required; lighting uses the vanilla environments.",
  },
  {
    icon: "lock",
    title: "Private",
    text: "Saber Tooth only talks to BeatSaver when you search or download there, to BeatMods when you check or install mods in Settings, to YouTube for a pasted link's title, and to the beat-analyser when it needs the audio.",
  },
  {
    icon: "shield",
    title: "Your maps are safe",
    text: "Fix, Apply and Crop write new folders. Only Save over this map in Crop and Delete change an existing folder, and both ask first.",
  },
];

function CardHead({ icon, title }: { icon: IconName; title: string }) {
  return (
    <div className="about-card-head">
      <span className="about-icon">
        <Icon name={icon} />
      </span>
      <h3>{title}</h3>
    </div>
  );
}

export function AboutPage() {
  useDocumentTitle("About");
  return (
    <PageShell
      active="about"
      title="About Saber Tooth"
      sectionClass="about-page"
      scroll="About content"
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
              <CardHead icon={f.icon} title={f.title} />
              <p>{f.text}</p>
            </li>
          ))}
        </ul>

        <h2>How to use it</h2>
        <ol className="about-timeline" aria-label="How to use it">
          {STEPS.map((step) => (
            <li key={step.title}>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </li>
          ))}
        </ol>

        <h2>Good to know</h2>
        <ul className="about-grid" aria-label="Good to know">
          {NOTES.map((n) => (
            <li key={n.title} className="about-card">
              <CardHead icon={n.icon} title={n.title} />
              <p>{n.text}</p>
            </li>
          ))}
        </ul>

        <h2>Links</h2>
        <ul className="about-grid" aria-label="Links">
          {LINKS.map((l) => (
            <li key={l.href} className="about-linkitem">
              <a
                className="about-card about-link-card"
                href={l.href}
                target="_blank"
                rel="noopener noreferrer"
              >
                <CardHead icon={l.icon} title={l.title} />
                <p>{l.text}</p>
              </a>
            </li>
          ))}
        </ul>

        <p className="muted about-version">Version {__APP_VERSION__}</p>
      </div>
    </PageShell>
  );
}
