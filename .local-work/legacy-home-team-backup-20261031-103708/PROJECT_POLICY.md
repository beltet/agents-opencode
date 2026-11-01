# Approved project policy

- **Repository:** `/home/bjohel`
- **Data classification:** `SHAREABLE — relevant non-secret project context approved for the configured cloud model providers`
- **AI execution mode:** `hybrid`
- **Enabled model providers:** `openai`, `opencode`
- **Default model:** `openai/gpt-5.5`
- **Cloud project content sharing:** `YES — relevant non-secret project content only`
- **Sensitive material:** Credentials, keys, `.env` and explicitly private content must never be shared. For mixed secret/shareable projects, use a separately isolated sanitized worktree before enabling cloud.
- **Approved remote:** `NONE` / `NONE`
- **Authorized Git remote actions:** NONE through `.opencode/tools/git_sync.py` only.
- **Protected branches:** `main`, `master`: wrapper blocks push/pull unless separately approved.
- **Resource budget:** Orchestrator estimates budget for each task: local = time/compute/memory; cloud = token/cost/time; hybrid = both. Modest stepwise increases only; significant budget escalation requires user consent.
- **Network:** Configured model endpoints and approved wrapper Git actions only. Web, other SSH/API/remote connections require approval.
- **Workspace:** Repository only, unless the user grants explicit additional scope and OS/environment restrictions permit it.
- **Documentation language:** English by default; user-facing conversation language follows user preference.

## Security notice

This project policy and `opencode.json` tool prompts are **not a hardened security boundary**. Any tool that the user authorizes may access other resources unless an external OS/container sandbox prevents it. An LLM call itself transmits its prompt context. Review provider configurations, plugins/MCP tools, Git hooks and environment variables separately. A provider with a local-sounding ID is not necessarily local: verify the actual endpoint yourself before using PRIVATE mode.
