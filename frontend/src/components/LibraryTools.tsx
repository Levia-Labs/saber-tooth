import * as Popover from "@radix-ui/react-popover";
import { useState } from "react";
import { learnLightshows } from "../api/client";
import type { JobRunner } from "../api/jobs";
import { useMediaQuery } from "../lib/hooks";
import { COMPACT_QUERY, TINY_QUERY } from "../lib/breakpoint";
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
 * Header actions. Wide: text buttons. Below 1100px: icon buttons with the same labels and Tips.
 * Below 480px: Generate stays and the rest move into a kebab menu with the same Tips.
 */
function ToolsBody({ learn, onResetColumns }: Props) {
  const iconOnly = useMediaQuery(COMPACT_QUERY);
  const tight = useMediaQuery(TINY_QUERY);
  const [open, setOpen] = useState(false);
  const generate = (
    <ActionLink
      icon="generate"
      label="Generate map"
      tip={TIPS.generate}
      to="/new"
      text={!iconOnly}
      variant={iconOnly ? undefined : "primary"}
      className={iconOnly ? "primary tap" : undefined}
    />
  );
  const run = () => void learn.run(learnLightshows);

  if (tight) {
    return (
      <div className="lib-tools">
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
    <div className="lib-tools">
      {generate}
      <ActionButton
        icon="learn"
        label="Learn lightshows"
        tip={TIPS.learn}
        text={!iconOnly}
        className={iconOnly ? "tap" : undefined}
        disabled={learn.busy}
        onClick={run}
      />
      <ActionButton
        icon="reset"
        label="Reset column widths"
        tip={TIPS.resetColumns}
        className={iconOnly ? "tap" : undefined}
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
