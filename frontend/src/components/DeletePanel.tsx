import { Icon } from "./icons";

/** The inline confirmation on the Delete tab: names the folder, then Delete or Back. */
export function DeletePanel({
  folder,
  disabled,
  pending = false,
  tip,
  onDelete,
  onBack,
}: {
  folder: string;
  disabled: boolean;
  /** The delete request is in flight: the button turns a spinner and cannot be pressed. */
  pending?: boolean;
  tip: string;
  onDelete: () => void;
  onBack: () => void;
}) {
  return (
    <section className="delete-panel" aria-labelledby="delete-title">
      <h2 id="delete-title">Delete permanently?</h2>
      <p>{`"${folder}" is removed from disk and cannot be undone.`}</p>
      <div className="row">
        <button
          type="button"
          className="btn danger"
          disabled={disabled || pending}
          title={tip}
          onClick={onDelete}
        >
          <Icon name={pending ? "spinner" : "trash"} />
          Delete
        </button>
        <button type="button" className="btn plain" onClick={onBack}>
          <Icon name="back" />
          Back
        </button>
      </div>
    </section>
  );
}
