import { useEffect, useRef } from "react";
import { useAnnounce, useWithdraw } from "../components/Announcer";
import { useVrMode } from "./VrMode";

/** Suggests the VR layout, as a bottom toast, when a headset runtime is active and nothing chose the mode. */
export function VrBanner() {
  const { showBanner, status, choose, dismissBanner } = useVrMode();
  const announce = useAnnounce();
  const withdraw = useWithdraw();
  const latest = useRef({ choose, dismissBanner });
  useEffect(() => {
    latest.current = { choose, dismissBanner };
  }, [choose, dismissBanner]);
  const runtime = status.runtime;

  useEffect(() => {
    if (!showBanner) {
      withdraw("vr-suggest");
      return;
    }
    announce({
      key: "vr-suggest",
      variant: "info",
      sticky: true,
      onDismiss: () => latest.current.dismissBanner(),
      title: "Headset in use: switch to VR layout?",
      message: `${runtime ?? "A headset runtime"} is running. The VR layout has large buttons and text for the headset.`,
      actions: [
        { label: "Switch", onClick: () => latest.current.choose("vr") },
        { label: "Not now", onClick: () => latest.current.dismissBanner() },
      ],
    });
  }, [showBanner, runtime, announce, withdraw]);

  return null;
}
