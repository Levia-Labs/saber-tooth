#!/bin/sh
# Start as root only to map user "app" to PUID/PGID, own /data, then drop privileges.
# /levels is user data and is never chowned: LEVELS_DIR must be writable by PUID.
set -eu

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

case "$PUID$PGID" in
  *[!0-9]* | "")
    echo "PUID and PGID must be numbers" >&2
    exit 64
    ;;
esac

if [ "$(id -u)" = "0" ]; then
  groupmod --non-unique --gid "$PGID" app
  usermod --non-unique --uid "$PUID" --gid "$PGID" app
  chown "$PUID:$PGID" /data
  exec setpriv --reuid "$PUID" --regid "$PGID" --clear-groups -- "$@"
fi
exec "$@"
