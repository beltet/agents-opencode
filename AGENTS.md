# Repository-local workflow (outside the installer-managed section)

## First check for every task or resumed session

Before other project work, check the Git boundary:

```sh
git status --short --untracked-files=normal
git ls-files
git ls-files -ci --exclude-standard
git diff --cached --name-status
```

Installed agents and generated configuration are local only: `.opencode/`,
`AGENTS.md`, `PROJECT_POLICY.md`, `AGENT_ACCESS_POLICY.json`, `opencode.json`
and `opencode.jsonc`. Store working notes, logs, decisions, handoffs and
checkpoints in `.local-work/` (ignored), not alongside distribution sources.
Installer backups are also ignored.

If local artifacts are tracked/staged, or unexpected new files appear, report
and resolve the boundary before proceeding; do not delete user files or
silently remove tracked files. Verify ignore coverage with `git check-ignore`.
Only curated installer code, source profiles (`lib/profiles/`), tests and
deliberately maintained product documentation belong in Git. Never force-add
local artifacts. Before any authorized commit, review the staged paths and
diff and stage explicit curated paths only; do not use `git add .` or `-A`.
Commits and pushes still require explicit user authorization.

Keep these local instructions outside the managed section so reinstalling
the agents preserves them. See README.md for the repository's Git boundary.

<!-- agents-opencode managed section START -->
## Installed OpenCode engineering team (managed)
Installed specialists (9): code-reviewer, orchestrator, performance-engineer, software-engineer, system-architect, technical-documenter, technical-educator, ux-ui-designer, verification-engineer.

Only activate a specialist when its expertise is required. If present, orchestrator coordinates; architect/documenter consultation is need-based, not an implementation gate. Follow `.opencode/team/TEAM_RULES.md`, `.opencode/team/WORKFLOW.md`, `PROJECT_POLICY.md` and `AGENT_ACCESS_POLICY.json`.
Implement, verify, integrate and continue through feasible authorized work. A checkpoint, commit, version boundary or specialist handoff is not a stopping condition. Do not invent approval gates.
Use compact active memory in the repository-designated local work area; read history selectively. The primary coordinates delegation; collaborator lists do not authorize nested agent calls.
Admit uncertainty; verify small experiments before costly simulations; hand off concise findings.
Project classification: **HYBRID**. A selected cloud model may see project context; never send secrets.
Technical agent profiles are written in English; communicate in the user’s requested language.
<!-- agents-opencode managed section END -->
