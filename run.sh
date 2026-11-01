#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$project_dir/src${PYTHONPATH:+:$PYTHONPATH}"
if [ -x "$project_dir/.venv/bin/python" ]; then
    exec "$project_dir/.venv/bin/python" -m sts_studio "$@"
fi
exec /usr/bin/python3 -m sts_studio "$@"
