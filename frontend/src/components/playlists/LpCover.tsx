import { useRef } from "react";
import { readCover } from "../../lib/lpedit";
import { Cover } from "../Chips";
import { Icon } from "../icons";
import { Tip } from "../Tip";

interface Props {
  url: string | null;
  onPick: (cover: { data: string; url: string }) => void;
  onError: (message: string) => void;
}

/** The map page's cover with an edit icon over it; the picked image shows at once. */
export function LpCover({ url, onPick, onError }: Props) {
  const file = useRef<HTMLInputElement>(null);
  const change = async (f: File | undefined) => {
    if (!f) return;
    const read = await readCover(f);
    if (typeof read === "string") onError(read);
    else onPick(read);
  };
  return (
    <div className="lp-cover-edit">
      <Cover url={url} big />
      <Tip text="Upload a cover (PNG or JPEG, up to 2 MB)">
        <button
          type="button"
          className="lp-cover-btn"
          aria-label="Change cover"
          onClick={() => file.current?.click()}
        >
          <Icon name="edit" />
        </button>
      </Tip>
      <input
        ref={file}
        type="file"
        accept="image/png,image/jpeg"
        aria-label="Cover file"
        hidden
        onChange={(e) => {
          void change(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
    </div>
  );
}
