# Security and enforcement boundaries

`agents-opencode` writes an **intent policy** and translates supported settings into OpenCode per-agent tool permissions. It is not a system firewall or execution sandbox.

| Control | What is actually applied | Limitations |
|---|---|---|
| Agent delegation | `permission.task` only allows configured specialists to be called by orchestrator; all subagents are denied nested Task calls | Direct user `@` calls and inherited/global configuration must be reviewed |
| Code reviewer | `edit: deny`, `bash: deny` | Other external tools/plugins may have separate capabilities |
| Orchestrator | Source editing denied by per-agent `edit`, with `.local-work/**` and `.agents-opencode/logs/**` allowed for coordination | General `bash` access is ASK by default and may bypass this restriction when authorized |
| Generic shell | ASK by default; selected simple Git patterns are gated | Alternative shells/wrappers can bypass command pattern matching; under `--auto`, ASK can become approval |
| Internet | `webfetch`/`websearch` action permissions | Domain/URL allowlists are *not* enforced on arbitrary HTTP tools, shell or plugins; webfetch URL-pattern rules unavailable in OpenCode 1 |
| External paths/shares | `external_directory` patterns where supported | Host process still has its operating-system access; network mount permissions cannot be emulated by prompt text |
| USB / serial | Policy records user intent | No real device-hardware mediation is implemented |
| Firmware | Known programming command names are conservatively denied via shell patterns | Cannot guarantee bypass prevention through alternate shells/APIs; explicitly configured firmware allowances are **not implemented as enforced grants** |
| Git remotes/branches | `git push` and related shell patterns plus user's policy | Not a Git server-side remote/branch allowlist; requires server-side protections and restricted SSH keys |
| Git SSH | Remote URL, author, identity path metadata; local Git config via confirmed `git-apply` | SSH key path is not automatically installed/configured or copied |
| Secrets | Prompt guidance; `.env` patterns require ASK | Process filesystem access and shell tools can bypass; rely on OS isolation |

**Recommended for unattended execution:** use a dedicated non-privileged user inside a restricted VM/container, minimal mounts, filtered outbound connections, protected branches, limited Git server access, and never expose firmware programmer nodes unless specifically needed. Explicit `deny` rules survive OpenCode's auto approval, but only for operations the tool permission system observes.

The Go manager does not run an AI model, discover hardware or fetch project files from the internet by itself; `opencode models` might contact providers because OpenCode owns model discovery. No secrets are stored by the manager. Backups can include user configuration content; avoid publishing project-local backups.
