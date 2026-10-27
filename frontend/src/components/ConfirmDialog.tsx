import * as Dialog from "@radix-ui/react-dialog";
import type { ReactElement } from "react";

interface Props {
  title: string;
  description: string;
  confirmLabel: string;
  onConfirm: () => void;
  /** The element that opens the dialog; it receives focus again when the dialog closes. */
  children: ReactElement;
}

export function ConfirmDialog({ title, description, confirmLabel, onConfirm, children }: Props) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>{children}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="modal">
          <Dialog.Title>{title}</Dialog.Title>
          <Dialog.Description>{description}</Dialog.Description>
          <div className="row">
            <Dialog.Close className="btn plain">Cancel</Dialog.Close>
            <Dialog.Close className="btn primary" onClick={onConfirm}>
              {confirmLabel}
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
