#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python -m mechanical_video.cli batch "$@"
exec .venv/bin/python -m mechanical_video.cli worker
