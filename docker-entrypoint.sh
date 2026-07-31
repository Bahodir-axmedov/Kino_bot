#!/bin/sh
# Railway (and most container platforms) mount a persistent volume at
# /data fresh on every deploy/restart. That mount is root-owned by
# default, which silently overwrites the "chown appuser:appuser /data"
# done at image build time -- so the app (running as the unprivileged
# "appuser") gets "Permission denied" the moment it tries to create
# /data/logs, /data/backups, or the SQLite file under /data.
#
# This entrypoint runs as root (the image no longer switches user at
# build time), fixes ownership of whatever got mounted at /data, then
# drops privileges to "appuser" via gosu before exec-ing the real
# command -- so the app still never runs as root, but the volume is
# always writable regardless of what permissions it was created with.
set -e

mkdir -p /data/backups /data/logs
chown -R appuser:appuser /data

exec gosu appuser "$@"
