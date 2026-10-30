from saber_tooth.service.core import Service
from saber_tooth.service.crop import crop_beats, crop_check, crop_map, crop_timeline
from saber_tooth.service.cropsuggest import crop_suggestions
from saber_tooth.service.errors import ApplyConflict, MapNotFound, MapUnreadable
from saber_tooth.service.fix import fix_map
from saber_tooth.service.generate import generate_map
from saber_tooth.service.relight import relight_map
from saber_tooth.service.util import map_id_for

Service.relight_map = relight_map  # type: ignore[attr-defined]  # see relight.py
Service.fix_map = fix_map  # type: ignore[attr-defined]  # one-click fix, see fix.py
Service.run_generate = generate_map  # type: ignore[attr-defined]  # one-step generate
Service.crop_timeline = crop_timeline  # type: ignore[attr-defined]  # crop highlight, see crop.py
Service.crop_suggestions = crop_suggestions  # type: ignore[attr-defined]  # Auto crop
Service.crop_check = crop_check  # type: ignore[attr-defined]
Service.crop_beats = crop_beats  # type: ignore[attr-defined]
Service.crop_map = crop_map  # type: ignore[attr-defined]

__all__ = ["ApplyConflict", "MapNotFound", "MapUnreadable", "Service", "map_id_for"]
