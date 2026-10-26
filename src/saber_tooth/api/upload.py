"""Multipart upload streaming with a size limit."""

import os
import shutil
import uuid
from pathlib import Path

from fastapi import Request
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from saber_tooth.api.core import ApiError

AUDIO_EXTENSIONS = {".ogg", ".egg", ".mp3", ".wav", ".flac", ".m4a"}


def _max_upload_bytes() -> int:
    try:
        return int(float(os.environ.get("MAX_UPLOAD_MB", "200")) * 1024 * 1024)
    except ValueError:
        return 200 * 1024 * 1024


async def _save_upload(request: Request, data: Path) -> Path:
    """Stream the multipart body to a temp file under data/uploads; enforce the size limit."""
    limit = _max_upload_bytes()
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit + 65536:
        raise ApiError(413, "upload too large")

    async def body():
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > limit + 65536:
                raise ApiError(413, "upload too large")
            yield chunk

    try:
        form = await MultiPartParser(request.headers, body(), max_files=1, max_fields=4).parse()
    except MultiPartException as exc:
        raise ApiError(400, f"bad multipart body: {exc.message}") from None
    upload = form.get("file")
    try:
        if not isinstance(upload, UploadFile):
            raise ApiError(400, "multipart field 'file' is required")
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in AUDIO_EXTENSIONS:
            raise ApiError(415, f"unsupported file type; use {' '.join(sorted(AUDIO_EXTENSIONS))}")
        if upload.size is not None and upload.size > limit:
            raise ApiError(413, "upload too large")
        folder = data / "uploads"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{uuid.uuid4().hex}{ext}"
        with target.open("wb") as out:
            shutil.copyfileobj(upload.file, out)
        return target
    finally:
        await form.close()
