import { useId, useState, type FormEvent } from "react";
import { generateFromFile, generateFromUrl, type Started } from "../../api/client";
import { isLink } from "../../lib/generate";
import { TIPS } from "../../lib/tips";
import { ActionButton } from "../Buttons";
import { DropZone } from "../DropZone";
import { CardHead } from "../settings/CardHead";

interface Props {
  busy: boolean;
  onRun: (label: string, source: "url" | "file", start: () => Promise<Started>) => void;
}

/** The way in: a YouTube link or an audio file, one Generate button, a problem shown under the field. */
export function AddCard({ busy, onRun }: Props) {
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const urlId = useId();
  const errorId = useId();

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const text = url.trim();
    if (file) {
      setProblem(null);
      onRun(file.name, "file", () => generateFromFile(file));
    } else if (text === "") {
      setProblem("Paste a YouTube link or drop an audio file.");
    } else if (!isLink(text)) {
      setProblem("That is not a link. Paste a YouTube URL.");
    } else {
      setProblem(null);
      onRun(text, "url", () => generateFromUrl(text));
    }
  };

  return (
    <section className="about-card gen-card" aria-labelledby="gen-add">
      <CardHead icon="generate" title="Add a song" id="gen-add" />
      <form className="gen-form" noValidate onSubmit={submit}>
        <label htmlFor={urlId}>YouTube URL</label>
        <input
          id={urlId}
          type="url"
          inputMode="url"
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          disabled={busy}
          aria-invalid={problem !== null}
          aria-describedby={problem ? errorId : undefined}
          onChange={(e) => {
            setUrl(e.target.value);
            setProblem(null);
          }}
        />
        <span className="gen-or">or</span>
        <DropZone
          file={file}
          onFile={(f) => {
            setFile(f);
            setProblem(null);
          }}
          onRefuse={setProblem}
          disabled={busy}
        />
        {problem && (
          <p id={errorId} className="gen-error" role="alert">
            {problem}
          </p>
        )}
        <div className="gen-actions" data-label-row>
          <ActionButton
            type="submit"
            icon="generate"
            label="Generate"
            tip={TIPS.generate}
            text
            variant="primary"
            disabled={busy}
          />
        </div>
      </form>
    </section>
  );
}
