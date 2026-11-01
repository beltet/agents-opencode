package assets

import "embed"

//go:embed agents/*.md team/*.md
var Templates embed.FS
