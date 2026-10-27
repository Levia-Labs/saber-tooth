"""Static frontend files with cache headers: hashed assets are immutable, the rest revalidates."""

from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

ASSET_CACHE = "public, max-age=31536000, immutable"
SHELL_CACHE = "no-cache"


class WebFiles(StaticFiles):
    """Vite writes content-hashed names under /assets/, so those never change in place."""

    def file_response(
        self, full_path, stat_result, scope: Scope, status_code: int = 200
    ) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        hashed = scope.get("path", "").startswith("/assets/") and status_code == 200
        response.headers["Cache-Control"] = ASSET_CACHE if hashed else SHELL_CACHE
        return response
