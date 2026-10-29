#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
command -v python3 >/dev/null || { echo 'Python 3 is required' >&2; exit 1; }
BASE="${XDG_DATA_HOME:-$HOME/.local/share}"
DEST="$BASE/agents-opencode"
BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
mkdir -p "$BASE" "$BIN"
STAGE=$(mktemp -d "$BASE/.agents-opencode-new.XXXXXX")
trap 'rm -rf -- "$STAGE"' EXIT
cp -R "$SOURCE/lib" "$STAGE/lib"
if [[ -d "$DEST" ]]; then
  # Old program versions are removed after a backup outside the active install tree.
  PREV="$BASE/.agents-opencode-previous-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  mv -- "$DEST" "$PREV"
  echo "Previous installation archived: $PREV"
fi
mv "$STAGE" "$DEST"
# User-defined profiles are personal data, not replaceable package templates.
if [[ -n "${PREV:-}" && -d "$PREV/custom-profiles" ]]; then
  mkdir -p "$DEST/custom-profiles"
  cp -Rn "$PREV/custom-profiles/." "$DEST/custom-profiles/"
fi
# Discard the superseded central program after user-authored profiles were migrated.
if [[ -n "${PREV:-}" && -d "$PREV" ]]; then
  rm -rf -- "$PREV"
  echo "Removed old central agent manager installation."
fi
trap - EXIT
install -m 0755 "$SOURCE/agents-opencode" "$BIN/agents-opencode"
# Old programs outside this managed path are not deleted (may belong to user).
# Other project files and OpenCode configurations are never removed by this system installer.
echo "Installed: $BIN/agents-opencode"
echo "Run: agents-opencode"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "Add to PATH: $BIN (fish: fish_add_path -U $BIN)";; esac
