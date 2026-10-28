import { CROP_TIPS } from "../lib/crop";
import { ActionButton } from "./Buttons";
import { ConfirmDialog } from "./ConfirmDialog";

/** "Save as new map" and, next to it, "Save over this map" behind a confirmation dialog.
 * The overwrite is not offered while a job runs on the map. */
export function CropSave(props: {
  folder: string;
  disabled: boolean;
  busy: boolean;
  onSave: (replace: boolean) => void;
}) {
  return (
    <>
      <ActionButton
        icon="apply"
        label="Save as new map"
        tip={CROP_TIPS.create}
        text
        variant="accent"
        disabled={props.disabled}
        onClick={() => props.onSave(false)}
      />
      {!props.busy && (
        <ConfirmDialog
          title="Replace this map?"
          description={`The map files in "${props.folder}" are replaced by the cropped version. The old version cannot be restored.`}
          confirmLabel="Replace map"
          danger
          onConfirm={() => props.onSave(true)}
        >
          <ActionButton
            icon="apply"
            label="Save over this map"
            tip={CROP_TIPS.replace}
            text
            variant="warning"
            disabled={props.disabled}
          />
        </ConfirmDialog>
      )}
    </>
  );
}
