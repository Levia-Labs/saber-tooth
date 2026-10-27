import { Logo } from "../components/Logo";
import { useDocumentTitle } from "../lib/hooks";

const LINKS = [
  { href: "https://github.com/Levia-Labs/saber-tooth", label: "saber-tooth on GitHub" },
  { href: "https://levialabs.net", label: "Levia Labs" },
  { href: "https://github.com/Levia-Labs/beat-analyser", label: "beat-analyser (companion)" },
  { href: "https://github.com/Levia-Labs/Crepidoma", label: "Crepidoma (companion)" },
];

export function AboutPage() {
  useDocumentTitle("About");
  return (
    <section className="page about">
      <Logo size={72} />
      <h1 tabIndex={-1} data-page-heading>
        About saber-tooth
      </h1>
      <p className="about-lead">
        saber-tooth is a local tool that makes Beat Saber custom maps playable. One Fix click adds
        missing difficulties (Easy to Expert+) and fixes impossible or uncomfortable patterns, then
        saves a new copy next to the original. Your original map is never changed.
      </p>

      <h2>What it does</h2>
      <ol>
        <li>Fixes maps in your library.</li>
        <li>
          Finds and downloads maps from BeatSaver, with filters BeatSaver itself lacks, for example
          maps that have Easy, Normal and Hard.
        </li>
        <li>Generates new maps from a song.</li>
        <li>
          Lights maps that still use the default environment, with vanilla lighting only. No mods
          are required.
        </li>
      </ol>

      <h2>How to use it</h2>
      <ol>
        <li>Open the Library.</li>
        <li>Press Fix on a map.</li>
        <li>Play the &quot;[saber-tooth]&quot; copy in Beat Saber.</li>
      </ol>

      <h2>Privacy</h2>
      <p>
        saber-tooth runs on your computer. It only talks to BeatSaver when you search or download
        there.
      </p>

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
    </section>
  );
}
