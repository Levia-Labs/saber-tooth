import { useId, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { generateFromFile, generateFromUrl } from "../api/client";
import { useGenerate } from "../api/generate";
import { useAnnounce } from "../components/Announcer";
import { ActionButton } from "../components/Buttons";
import { DropZone } from "../components/DropZone";
import { Icon } from "../components/icons";
import { isLink } from "../lib/generate";
import { libraryHref, useDocumentTitle } from "../lib/hooks";
import { TIPS } from "../lib/tips";

const WARN_KEY = "generate-input";

/** One card: paste a YouTube link or drop an audio file, press Generate, land on the finished map. */
export function NewPage() {
  useDocumentTitle("Generate map");
  const announce = useAnnounce();
  const gen = useGenerate();
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const urlId = useId();

  const warn = (title: string) => announce({ key: WARN_KEY, variant: "warning", title });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const text = url.trim();
    if (file) {
      void gen.run(file.name, () => generateFromFile(file));
    } else if (text === "") {
      warn("Paste a YouTube link or drop an audio file.");
    } else if (!isLink(text)) {
      warn("That is not a link. Paste a YouTube URL.");
    } else {
      void gen.run(text, () => generateFromUrl(text));
    }
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
      <form className="gen-form" noValidate onSubmit={submit}>
        <label htmlFor={urlId}>YouTube URL</label>
        <input
          id={urlId}
          type="url"
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          disabled={gen.busy}
          onChange={(e) => setUrl(e.target.value)}
        />
        <span className="gen-or">or</span>
        <DropZone file={file} onFile={setFile} onRefuse={warn} disabled={gen.busy} />
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
    </section>
  );
}
