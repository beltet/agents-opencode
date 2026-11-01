# Project-local agent teams

- Owner authorized retiring the old home-directory team, with backup and unrelated
  settings retained; all active team installations must be project-local.
- Backup: `.local-work/legacy-home-team-backup-20261031-103708/`, 32 reviewed files
  with verified SHA256 manifest. Contains original home opencode.json and 31
  removed legacy profiles, team rules, helper scripts and home policy/instructions.
- Removed all 23 `~/.opencode/agents/*.md`, three team templates, two old team
  tools, `~/AGENTS.md`, `~/PROJECT_POLICY.md`, `~/PROJECT_RUNTIME_POLICY.json`.
- Removed only team-related default_agent/instructions/subagent_depth/agent
  mappings and the old git_sync permission from `~/opencode.json`; retained all
  other configuration exactly (verified against the backup).
- OpenCode binary, provider configuration/authentication, installed dependencies
  and existing per-project installations were retained.
- Code changes: `lib/manager.py` rejects home/global destinations and managed
  symlink paths escaping the project before install/refresh/policy writes.
  README describes project-local ownership and refresh semantics.
- Added tests for rejected home/global destinations, escaping symlinks and two
  independent projects with differing profiles/models.
- Full suite: 87 tests run, 85 passed, 2 native-Windows skips. `git diff --check`
  and Git boundary checks passed. Only README, manager, manager tests modified.
- Installed updated central tool with `python3 install.py --lang sv`. Actual
  `agents-opencode install /home/bjohel --lang sv` rejected before writing.
- OpenCode 1.19.5 `debug config` in home and this repo: no legacy team inherited.
  All 23 new project profiles loaded without caps using actual HOME/global config
  in a disposable project (`check_agent_runtime.py --real-home`), no model invoked.
- This repo still has no locally installed team/manifest; use normal project
  wizard to choose roles, classification and models. Other projects untouched.
- Restart OpenCode to unload the old session configuration. No new commit/push
  requested for these follow-up changes; earlier workflow commit is 1da0b79.
