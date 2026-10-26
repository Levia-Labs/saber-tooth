import logging
import re
import wave
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw

from saber_tooth.analysis import Analysis
from saber_tooth.checks import RULES, run_checks
from saber_tooth.generator import generate_all, tempo_map
from saber_tooth.lightshow import Templates, build_lightshow
from saber_tooth.mapio import write_map
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import Beatmap, MapInfo

log = logging.getLogger(__name__)

VANILLA_ENVIRONMENT = "NiceEnvironment"
MAPPER = "saber-tooth"
AUTHOR = "Unknown"
SONG_FILE = "song.egg"
COVER_FILE = "cover.png"
COVER_SIZE = 512
PREVIEW_FRACTION = 0.25
PREVIEW_DURATION = 10


def _clean(title: str) -> str:
    return " ".join(re.sub(r"[^A-Za-z0-9 -]", "", title).split())


def folder_name(title: str) -> str:
    clean = _clean(title) or "Untitled"
    slug = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-") or "untitled"
    return f"st-{slug} ({clean} - {MAPPER})"


def _cover(path: Path, title: str) -> None:
    img = Image.new("RGB", (COVER_SIZE, COVER_SIZE))
    draw = ImageDraw.Draw(img)
    for y in range(COVER_SIZE):
        shade = 12 + 36 * y // COVER_SIZE
        draw.line([(0, y), (COVER_SIZE, y)], fill=(shade // 2, shade // 3, shade + 8))
    lines = [title[i : i + 28] for i in range(0, len(title), 28)][:6] or [""]
    top = COVER_SIZE // 2 - 6 * len(lines)
    for k, line in enumerate(lines):
        width = draw.textlength(line)
        draw.text(((COVER_SIZE - width) / 2, top + 12 * k), line, fill=(230, 230, 240))
    img.save(path, format="PNG")


def _length(a: Analysis, wav: Path) -> float:
    try:
        with wave.open(str(wav), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, EOFError, OSError):
        return a.beats[-1] if a.beats else 0.0


def _apply_lightshow(bm: Beatmap, timing, templates: Templates | None, a: Analysis, seed: int):
    if templates is None or not any(templates.units.values()):
        log.warning("no lightshow templates; map keeps a vanilla environment without lighting")
        return
    payload = build_lightshow(bm, timing, templates, a, seed)
    bm.info.environment = payload.environment
    bm.info.color_scheme = payload.color_scheme
    for name, (events, boosts, groups) in payload.events.items():
        d = bm.difficulties[name]
        d.events = events
        d.boosts = boosts
        for key in BOX_KEYS:
            d.raw[key] = groups.get(key, [])


def assemble_new(
    a: Analysis,
    templates: Templates | None,
    out: Path,
    seed: int,
    encode: Callable[[Path, Path], None],
) -> Beatmap:
    if a.audio is None or not a.audio.is_file():
        raise ValueError("analysis has no audio file")
    timing, diffs = generate_all(a, seed)
    start = round(_length(a, a.audio) * PREVIEW_FRACTION, 3)
    info = MapInfo(
        song_name=a.name,
        sub_name="",
        author=AUTHOR,
        mapper=MAPPER,
        bpm=tempo_map(a)[0],
        song_file=SONG_FILE,
        cover_file=COVER_FILE,
        preview_start=start,
        preview_duration=PREVIEW_DURATION,
        environment=VANILLA_ENVIRONMENT,
    )
    bm = Beatmap(info, diffs, folder_name(a.name))
    _apply_lightshow(bm, timing, templates, a, seed)
    findings = run_checks(bm, a, rules=set(RULES))
    if findings:
        first = findings[0]
        raise ValueError(
            f"generated map has {len(findings)} findings; first: "
            f"{first.rule} {first.difficulty} @ {first.beat_start}: {first.message}"
        )
    out.mkdir(parents=True, exist_ok=True)
    encode(a.audio, out / SONG_FILE)
    _cover(out / COVER_FILE, a.name)
    write_map(bm, out, None)
    return bm
