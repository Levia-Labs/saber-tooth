"""Style and metadata commands: environments, songmeta, and the style options of gen-url."""

import argparse
import json
import sys
from pathlib import Path

from saber_tooth.environments import format_catalogue
from saber_tooth.mapio import MapParseError
from saber_tooth.songmeta import describe
from saber_tooth.style import parse_style


def style_from_args(args: argparse.Namespace) -> dict | None:
    """The style from --style JSON, --environment and --color ROLE=#rrggbb; ValueError if bad."""
    raw: dict = {}
    if args.style:
        try:
            raw = json.loads(args.style)
        except ValueError:
            raise ValueError("--style must be JSON") from None
        if not isinstance(raw, dict):
            raise ValueError("--style must be a JSON object")
    if args.environment:
        raw = {**raw, "environment": args.environment}
    colors = dict(raw.get("colors") or {}) if isinstance(raw.get("colors"), dict) else {}
    for item in args.color or []:
        role, _, value = item.partition("=")
        colors[role] = value
    if colors:
        raw = {**raw, "colors": colors}
    style = parse_style(raw or None)
    return style.to_dict() if style else None


def _cmd_environments(args: argparse.Namespace) -> int:
    print(format_catalogue())
    return 0


def _cmd_songmeta(args: argparse.Namespace) -> int:
    try:
        print(json.dumps(describe(Path(args.path)), ensure_ascii=False))
    except (OSError, MapParseError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    """Add the environments and songmeta subcommands."""
    ev = sub.add_parser("environments", help="list the environment catalogue")
    ev.set_defaults(func=_cmd_environments)
    sm = sub.add_parser("songmeta", help="print title, artist, duration and bpm as JSON")
    sm.add_argument("path", help="audio file or map folder")
    sm.set_defaults(func=_cmd_songmeta)
