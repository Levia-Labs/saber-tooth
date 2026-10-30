import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/library.css";
import "./styles/rows.css";
import "./styles/skeletons.css";
import "./styles/chips.css";
import "./styles/overlays.css";
import "./styles/filters.css";
import "./styles/datepicker.css";
import "./styles/page.css";
import "./styles/generate.css";
import "./styles/pill.css";
import "./styles/beatsaver.css";
import "./styles/barslot.css";
import "./styles/playlists.css";
import "./styles/preview.css";
import "./styles/crop.css";
import "./styles/alerts.css";
import "./styles/emptystate.css";
import "./styles/about.css";
import "./styles/settings.css";
import "./styles/jobs.css";
import "./styles/localplaylists.css";
import "./styles/vrmode.css";
import "./styles/vr.css";

const root = document.getElementById("root");
if (!root) throw new Error("missing #root");
createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
