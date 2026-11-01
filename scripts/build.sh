#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
go test ./...
mkdir -p dist
for target in linux/amd64 linux/arm64 windows/amd64 windows/arm64 darwin/amd64 darwin/arm64; do
  os=${target%/*}; arch=${target#*/}; ext=""; [ "$os" = windows ] && ext=".exe"
  echo "Building ${os}/${arch}"
  GOOS="$os" GOARCH="$arch" CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o "dist/agents-opencode-${os}-${arch}${ext}" ./cmd/agents-opencode
done
(cd dist && sha256sum agents-opencode-* > SHA256SUMS)
echo 'Build artifacts in dist/. These are cross-compiled; runtime test on target OS is still required.'
