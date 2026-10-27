import * as Checkbox from "@radix-ui/react-checkbox";
import { Icon } from "../icons";

/** Labelled checkbox row used by the BeatSaver filter bodies. */
export function Box(props: {
  id: string;
  checked: boolean;
  onToggle: () => void;
  children: string;
}) {
  return (
    <div className="check">
      <Checkbox.Root
        id={props.id}
        className="checkbox"
        checked={props.checked}
        onCheckedChange={props.onToggle}
      >
        <Checkbox.Indicator>
          <Icon name="approve" />
        </Checkbox.Indicator>
      </Checkbox.Root>
      <label htmlFor={props.id}>{props.children}</label>
    </div>
  );
}
