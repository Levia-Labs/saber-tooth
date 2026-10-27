FROM python:3.12-slim

# ffmpeg version follows the Debian base image, so it is not pinned
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

RUN useradd --create-home --uid 1000 app \
    && mkdir /data \
    && chown app:app /data

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# No USER here: the entrypoint starts as root only to apply PUID/PGID, then drops to app.
ENV PUID=1000 PGID=1000
EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/api/maps', timeout=4)"]

# nosemgrep: dockerfile.security.missing-user-entrypoint.missing-user-entrypoint -- container starts as root only so the entrypoint can apply PUID/PGID, then setpriv drops privileges (docs/adr/0009)
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# nosemgrep: dockerfile.security.missing-user.missing-user -- container starts as root only so the entrypoint can apply PUID/PGID, then setpriv drops privileges (docs/adr/0009)
CMD ["/app/.venv/bin/uvicorn", "saber_tooth.api:app", "--host", "0.0.0.0", "--port", "8100"]
