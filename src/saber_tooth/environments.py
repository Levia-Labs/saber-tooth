"""Catalogue of the vanilla environments that have a learned lightshow template.

Each entry says what the stage feels like (moods, valence, energy, intensity), what it looks like
(setting), which genres suit it and the palette it is written with by default. Valence, energy
and intensity run from 0 to 1. Names match the keys of the bundled lightshow templates."""

from dataclasses import dataclass

# Colour roles of a style; the info.dat keys they are written under.
COLOR_ROLES: dict[str, str] = {
    "saber_left": "saberAColor",
    "saber_right": "saberBColor",
    "env_left": "environmentColor0",
    "env_right": "environmentColor1",
    "env_left_boost": "environmentColor0Boost",
    "env_right_boost": "environmentColor1Boost",
    "obstacle": "obstaclesColor",
}


@dataclass(frozen=True)
class Environment:
    name: str
    moods: tuple[str, ...]
    valence: float  # 0 dark or sad, 1 bright or joyful
    energy: float  # 0 still, 1 driving
    intensity: float  # 0 soft, 1 aggressive
    setting: str
    genres: tuple[str, ...]
    palette: dict[str, str]  # colour role -> "#rrggbb"


def _pal(*hexes: str) -> dict[str, str]:
    return dict(zip(COLOR_ROLES, hexes, strict=True))


def _env(name, moods, vei, setting, genres, palette) -> Environment:
    return Environment(
        name, tuple(moods.split()), *vei, setting, tuple(genres.split()), _pal(*palette.split())
    )


# fmt: off
# name, moods, (valence, energy, intensity), setting, genres, palette:
# saber L, saber R, env L, env R, env L boost, env R boost, obstacle
_ROWS = (
    ("BTSEnvironment", "joyful glossy energetic", (0.85, 0.80, 0.50),
     "pop concert stage with rising light panels and confetti glow",
     "k-pop pop dance",
     "#ff3b7f #3bb8ff #ff5fa2 #5fd0ff #ffd1e6 #d1f0ff #a259ff"),
    ("BigMirrorEnvironment", "open modern versatile", (0.65, 0.65, 0.50),
     "mirrored floor under tall light pillars in a wide hall",
     "electronic pop house dance",
     "#ff2d55 #2d9bff #ff6b88 #5db6ff #ffc2cf #c2e4ff #7a5cff"),
    ("BillieEnvironment", "dark moody intimate eerie", (0.20, 0.35, 0.40),
     "dim stage with sickly green neon and heavy shadow",
     "dark-pop alt-pop trap whisper-pop",
     "#7cff2e #1e1e1e #2eff8a #3a3a3a #c8ffa0 #8a8a8a #1fa34a"),
    ("DragonsEnvironment", "epic anthemic dramatic powerful", (0.55, 0.75, 0.70),
     "arena stage with rising flame-coloured beams and a big sky",
     "rock alt-rock anthem pop-rock",
     "#ff7a1a #1a8cff #ff9a45 #4aa8ff #ffd2a0 #a8d4ff #e8e8e8"),
    ("FitBeatEnvironment", "motivating upbeat sporty relentless", (0.75, 0.90, 0.65),
     "gym-club room with pulsing bars and scanning lasers",
     "workout edm dance-pop drum-and-bass",
     "#ff2a8a #20e8ff #ff59a8 #4df0ff #ffb3d6 #b3f8ff #c8ff2a"),
    ("HalloweenEnvironment", "spooky playful eerie", (0.30, 0.50, 0.50),
     "haunted night scene with orange glow and purple mist",
     "halloween horror-synth orchestral novelty",
     "#ff7a00 #8a2be2 #ff9a30 #a85cf0 #ffd08a #d9b3ff #2ecc40"),
    ("KDAEnvironment", "glamorous fierce confident", (0.70, 0.80, 0.70),
     "neon-lit esports stage with gold trim and sharp beams",
     "k-pop hip-hop pop trap",
     "#ff2f9c #00d4c8 #ff62b8 #35e8dc #ffc2e2 #a8fff8 #ffd24a"),
    ("KaleidoscopeEnvironment", "dreamy trippy hypnotic floating", (0.60, 0.45, 0.35),
     "mirrored psychedelic tunnel of rotating colour shards",
     "ambient psychedelic synth chillwave downtempo",
     "#b84dff #33e0c4 #d06bff #5cf0d8 #ecc2ff #b8fff0 #ff8ad8"),
    ("LinkinParkEnvironment", "angry raw tense cathartic", (0.25, 0.80, 0.85),
     "gritty industrial stage with harsh strobes and cold light",
     "nu-metal alt-rock rap-rock post-hardcore",
     "#ff5a1f #2d6bff #ff8a50 #6a96ff #ffc8a8 #bcd0ff #9a9a9a"),
    ("MetallicaEnvironment", "aggressive heavy relentless menacing", (0.15, 0.90, 1.00),
     "black stage with blood-red lamps and hard white flashes",
     "metal thrash hard-rock heavy-metal",
     "#ff1a1a #f2f2f2 #ff4a4a #ffffff #ff9a9a #ffffff #7a0000"),
    ("NiceEnvironment", "balanced bright clean friendly", (0.65, 0.55, 0.40),
     "the classic neon corridor with side lasers and a ring of light",
     "pop electronic indie dance rock",
     "#ff3030 #2f9bff #ff5a5a #5ab4ff #ffb3b3 #b3dcff #ffffff"),
    ("OriginsEnvironment", "pure classic neutral focused", (0.50, 0.55, 0.45),
     "the original tunnel of rings and lasers, minimal and readable",
     "electronic any classic game-music",
     "#e83a3a #3a9ae8 #e85a5a #5ab0e8 #f0b0b0 #b0d4f0 #dcdcdc"),
    ("PanicEnvironment", "theatrical wild flamboyant frantic", (0.55, 0.85, 0.75),
     "carnival-theatre stage with red curtains and golden spots",
     "pop-punk emo theatrical-rock alt-pop",
     "#e8142a #f2c230 #ff4a5a #ffd96a #ffb0b8 #fff0b0 #4a1a6a"),
    ("PyroEnvironment", "fiery intense explosive", (0.40, 0.85, 0.90),
     "fire-lit stage with flame jets and ember-orange haze",
     "rock metal edm dubstep",
     "#ff4a00 #ffb300 #ff7a2a #ffd04a #ffc8a0 #fff0b0 #b81400"),
    ("RockMixtapeEnvironment", "warm nostalgic gritty live", (0.60, 0.65, 0.60),
     "club stage with warm amber spots, speaker stacks and a cassette backdrop",
     "classic-rock indie garage-rock blues-rock",
     "#ff8a1f #1fb8ff #ffa650 #50c8ff #ffd9a8 #b0e6ff #e8e0c8"),
    ("RocketEnvironment", "fast competitive bright futuristic", (0.70, 0.85, 0.65),
     "arena of boost trails with a blue-and-orange team glow",
     "drum-and-bass electro big-room dubstep",
     "#ff8a1a #1a8aff #ffaa4a #4aaaff #ffd8a8 #a8d4ff #e8f0ff"),
    ("TheWeekndEnvironment", "nocturnal sleek seductive retro", (0.35, 0.60, 0.55),
     "after-dark city with red neon, scan lines and deep purple fog",
     "synthwave r&b synth-pop dark-pop",
     "#ff1f3d #7a2bff #ff4a60 #9a55ff #ffa8b4 #cfb0ff #1fe0ff"),
    ("TimbalandEnvironment", "urban slick groovy smooth", (0.60, 0.60, 0.50),
     "studio-club room with gold light bars and cool blue wash",
     "hip-hop r&b rap pop",
     "#ffc21a #2a7aff #ffd54a #5a9aff #ffecb0 #b0ccff #c8c8c8"),
    ("TriangleEnvironment", "geometric cold precise driving", (0.50, 0.75, 0.65),
     "sharp triangle lattices pulsing in cyan and magenta",
     "techno electro trance idm",
     "#00e5ff #ff2ad4 #4af0ff #ff5ae0 #b0f8ff #ffb0f0 #8a5cff"),
    ("WeaveEnvironment", "flowing calm tender airy", (0.70, 0.30, 0.20),
     "soft woven ribbons of light drifting over open dark",
     "ambient indie-folk chillout acoustic lo-fi",
     "#3ad8c8 #a066ff #62e8da #b88aff #b8f6f0 #e0ccff #ffb0d8"),
)
# fmt: on

CATALOGUE: tuple[Environment, ...] = tuple(_env(*r) for r in _ROWS)
BY_NAME: dict[str, Environment] = {e.name: e for e in CATALOGUE}


def names() -> list[str]:
    return sorted(BY_NAME)


def format_catalogue(catalogue: tuple[Environment, ...] = CATALOGUE) -> str:
    """One compact block per environment: moods, scores, setting, genres and palette."""
    lines = []
    for e in sorted(catalogue, key=lambda e: e.name):
        lines.append(
            f"{e.name} | {' '.join(e.moods)} | v{e.valence:.2f} e{e.energy:.2f} i{e.intensity:.2f}"
            f" | {e.setting} | {' '.join(e.genres)} | {' '.join(e.palette.values())}"
        )
    return "\n".join(lines)
