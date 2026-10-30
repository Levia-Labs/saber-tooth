import * as Popover from "@radix-ui/react-popover";
import { useState } from "react";
import { learnLightshows } from "../api/client";
import type { JobRunner } from "../api/jobs";
import { useMediaQuery } from "../lib/hooks";
import { TINY_QUERY } from "../lib/breakpoint";
import { TIPS } from "../lib/tips";
import { InBar } from "./BarSlot";
import { ActionButton, ActionLink } from "./Buttons";
import { Icon } from "./icons";
import { Tip } from "./Tip";

interface Props {
  learn: JobRunner;
  onResetColumns: () => void;
}

/**
 * Header actions. Text buttons whose labels collapse to icons when the row runs out of room.
 * Below 480px: Generate stays and the rest move into a kebab menu with the same Tips.
 */
function ToolsBody({ learn, onResetColumns }: Props) {
  const tight = useMediaQuery(TINY_QUERY);
  const [open, setOpen] = useState(false);
  const generate = (
    <ActionLink
      icon="generate"
      label="Generate map"
      tip={TIPS.generate}
      to="/new"
      text
      variant="primary"
    />
  );
  const run = () => void learn.run(learnLightshows);

  if (tight) {
    return (
      <div className="lib-tools" data-label-row>
        {generate}
        <Popover.Root open={open} onOpenChange={setOpen}>
          <Tip text="More actions.">
            <Popover.Trigger className="btn icon tap" aria-label="More actions">
              <Icon name="more" />
            </Popover.Trigger>
          </Tip>
          <Popover.Portal>
            <Popover.Content className="popover kebab" align="end" sideOffset={6}>
              <Tip text={TIPS.learn}>
                <button
                  type="button"
                  className="btn plain kebab-item"
                  disabled={learn.busy}
                  onClick={() => {
                    setOpen(false);
                    run();
                  }}
                >
                  <Icon name="learn" />
                  <span>Learn lightshows</span>
                </button>
              </Tip>
              <Tip text={TIPS.resetColumns}>
                <button
                  type="button"
                  className="btn plain kebab-item"
                  onClick={() => {
                    setOpen(false);
                    onResetColumns();
                  }}
                >
                  <Icon name="reset" />
                  <span>Reset column widths</span>
                </button>
              </Tip>
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
      </div>
    );
  }

  return (
    <div className="lib-tools" data-label-row>
      {generate}
      <ActionButton
        icon="learn"
        label="Learn lightshows"
        tip={TIPS.learn}
        text
        disabled={learn.busy}
        onClick={run}
      />
      <ActionButton
        icon="reset"
        label="Reset column widths"
        tip={TIPS.resetColumns}
        onClick={onResetColumns}
      />
    </div>
  );
}

export function LibraryTools(props: Props) {
  return (
    <InBar>
      <ToolsBody {...props} />
    </InBar>
  );
}
