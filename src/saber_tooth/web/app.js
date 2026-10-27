import { el, guard, jobGuard, runJob, api, setStatus } from "./util.js";
import { start } from "./router.js";
import { showLibrary } from "./library.js";
import { showMap } from "./mappage.js";
import { showNew } from "./newmap.js";
import { installTooltips } from "./tooltip.js";
import { TIPS } from "./tips.js";

const main = document.getElementById("main");

function notFound() {
  main.replaceChildren(
    el("h2", {}, "Page not found"),
    el("p", {}, el("a", { href: "/" }, "Back to the library")),
  );
  return "Page not found";
}

async function render(route, token) {
  const gen = document.getElementById("gen-link");
  if (route.name === "new") gen.setAttribute("aria-current", "page");
  else gen.removeAttribute("aria-current");
  try {
    if (route.name === "library") return showLibrary();
    if (route.name === "map") return await showMap(route.id, token);
    if (route.name === "new") return showNew();
  } catch (err) {
    setStatus(`Error: ${err.message}`);
    return "";
  }
  return notFound();
}

installTooltips();
document.getElementById("gen-link").dataset.tip = TIPS.generate;
const learn = document.getElementById("learn");
learn.dataset.tip = TIPS.learn;
learn.addEventListener(
  "click",
  jobGuard(async () => {
    await runJob("Learn lightshows", await api.learn());
  }),
);
guard(() => start(render))();
