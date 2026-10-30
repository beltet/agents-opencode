#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 "$SOURCE/install.py" "$@"
