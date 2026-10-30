# OpenCode Agentteam — portable installer v2.1.0

A portable installer and manager for an engineering-agent team for **OpenCode 1.x** (designed for v1.19.5). It includes 23 specialist profiles and shared team instructions in English. The manager offers Swedish and English UI. No model IDs, API keys, providers, or user-specific paths are preconfigured; each user selects models and permissions.

## Quick start

### Windows (native)

Requirements: Windows, Python 3.10 or later, Git, and OpenCode installed and configured separately. The installer itself is native Python and does not require Bash, administrator rights, Python packages, or a network connection. OpenCode has its own platform requirements; on Windows it may require Git Bash. Check OpenCode's own requirements—this installer does not install or validate Git Bash.

1. Download the **complete source archive** from GitHub using **Code → Download ZIP**. There is no separate release binary. Extract the complete archive; do not copy only the launcher or installer.
2. In Command Prompt, open the extracted folder and run:

   ```text
   install.cmd
   ```

   In PowerShell, use `Set-Location` to enter the extracted folder, then run `.\install.cmd` or `.\install.cmd --lang en` / `.\install.cmd --lang sv`.
   The installer asks for language first (Swedish or English; Enter selects English).
3. In Command Prompt, start `agents-opencode.cmd` from the extracted folder, or use the installed launcher:

   ```text
   "%LOCALAPPDATA%\agents-opencode\bin\agents-opencode.cmd"
   ```

   In PowerShell, use `& "$env:LOCALAPPDATA\agents-opencode\bin\agents-opencode.cmd"`.
   The installed command directory is **not added to PATH automatically**. Either run the launcher by its full path, or add the appropriate `%LOCALAPPDATA%` / `$env:LOCALAPPDATA` directory to your user PATH manually and open a new terminal. No administrator rights are required.
4. In a project folder, start the installed launcher by its full path as shown above, or use `agents-opencode.cmd` if its `bin` directory is on PATH. Choose **1** to configure the project. Append `--lang en` or `--lang sv` to select a language directly. Without the flag, the manager asks for language first on interactive startup; Enter defaults to English. In noninteractive use, the default is English.

OpenCode and its model providers must be installed/configured separately; the manager uses `opencode models` when you configure a project. The manager's installer does not download software or contact a network. If OpenCode's Windows runtime needs Git Bash, that is an OpenCode runtime requirement, not a requirement to run `install.cmd`.

### Linux

Requirements: Bash, Python 3.10 or later (standard library only), Git, and OpenCode installed/configured separately. Extract the complete archive, then run:

```bash
bash install.sh
```

The user launcher is `~/.local/bin/agents-opencode`; central files are in `${XDG_DATA_HOME:-~/.local/share}/agents-opencode/`. The command directory may need to be added to PATH manually. No root privileges or Python packages are required.

## Sharing the installer

Share the **complete curated source archive** (for example, the GitHub repository's **Code → Download ZIP** archive). It must contain the platform entry points, `lib/`, profiles, and documentation. Do not share a locally installed manager directory or generated project configuration as though it were the installer. User-specific files such as `opencode.json`, `AGENTS.md`, `PROJECT_POLICY.md`, `AGENT_ACCESS_POLICY.json`, and `.opencode/` are generated/configured locally and are not part of the curated distribution. There is no separate release ZIP/binary unless one is explicitly published in the future.

The optional `AGENT_CAST.md` is a fictional, lightly comic presentation of the 23 roles—not real people, identities, or relationships. It does not alter role instructions, authority, or behavior; humor is optional.

## Project setup

From a Git project directory, run `agents-opencode` on Linux or `agents-opencode.cmd` on Windows, then choose **1 – Install / configure**. In Windows CMD, change directory with `cd /d C:\path\to\project`; in PowerShell, use `Set-Location C:\path\to\project`. You may also pass a project path to the command.

The wizard:

1. Lets you choose all agents, the suggested core three, or a list/range of agent numbers. User-created roles can extend the list.
2. Runs the separately installed OpenCode command `opencode models` and shows its available model list for each selected agent. Choose a listed model, reuse the previous selection, inherit the caller's model, or keep an existing assignment where applicable. No model is preset. For `image-analyst`, select a model that supports image input.
3. Asks whether the project is PRIVATE, SHAREABLE, or HYBRID. PRIVATE requires you to verify that chosen endpoints are local; the tool cannot detect whether an alias or proxy forwards data to the cloud.
4. Offers permission presets and asks you to review individual permissions. You can separately configure mounted shares and path/network rules.
5. Shows a summary and asks for confirmation before writing project files.

The installer may offer to initialize a project as a Git repository. Existing project files that it changes are backed up. This does not mean every global or parent OpenCode configuration has been inspected; review your setup and backups.

## Manager commands

Commands accept an optional project path. On Windows, use the `.cmd` launcher; the launcher can be invoked from the extracted folder or the installed location above. Language flags may be given anywhere on the command line, for example `agents-opencode.cmd status C:\work\project --lang sv`.

| Action | Command |
| --- | --- |
| Install, migrate, or configure a project | `agents-opencode install` |
| Reassign selected models | `agents-opencode models-all` |
| Add/remove installed roles | `agents-opencode agents` |
| Edit permission choices | `agents-opencode permissions` |
| Edit path and network rules | `agents-opencode access` |
| Synchronize manually edited access policy | `agents-opencode sync-access` |
| Show project status | `agents-opencode status` |
| Create a reusable custom English agent | `agents-opencode add-agent` |
| Start OpenCode / continue latest session | `agents-opencode run` / `agents-opencode resume` |
| List available models | `agents-opencode list-models` |

The management UI language is selected per run; it is not a translation of generated agent profiles or project instructions, which remain English.

## Permissions and security

The project wizard configures OpenCode 1.x permissions (`permission`, `bash`, `task`, `agent`). **Do not use this generated format with OpenCode v2**, which uses a different configuration format.

You may set shell commands, file edits, Git push, internet-related tools, access outside the project, secrets, MCP/external services, package installation, hardware tools, and unattended launch to allow, ask, or deny. These settings are best-effort OpenCode tool permissions and agent behavior instructions—not a firewall, filesystem sandbox, or OS security boundary. Allowed shell commands and programs can access resources available to the host account and may bypass tool-level patterns. `--auto` approves `ask`; use `deny` for actions that must remain blocked. Real isolation requires OS-level controls such as a VM/container, restricted mounts, and network filtering.

The per-project `AGENT_ACCESS_POLICY.json` is an editable policy description. Its helper checks are advisory; configured model-provider traffic is separate from agent-initiated network requests. Read the detailed cautions below before using broad permissions or unattended mode.

## Per-project access policy

At first install, the wizard writes `AGENT_ACCESS_POLICY.json`. The project root is allowed for project work; outside paths default according to the selected permission profile. More specific path rules can allow or deny local folders and mounted shares. Network rules use hostnames, schemes, and optional ports. This policy and its generated instructions are **not a security sandbox**.

```json
{
  "version": 1,
  "advisory_only": true,
  "project_root": "C:\\work\\example",
  "filesystem": {
    "default_outside": {"read": "deny", "write": "deny"},
    "paths": [
      {"path": "D:\\team-documents", "kind": "network-share", "read": "allow", "write": "deny"}
    ]
  },
  "network": {
    "default": "deny",
    "hosts": [{"scheme": "https", "host": "docs.example.org", "access": "allow"}]
  }
}
```

This is illustrative only; the wizard generates a project-specific file. Use `agents-opencode access` to edit it interactively. After manual JSON edits, run `agents-opencode sync-access` and restart OpenCode. The access-check and access-fetch helper examples in generated project instructions use Python; on Windows, use the Python launcher available on your system (for example `py -3`).

OpenCode 1.x cannot restrict `webfetch` to individual hostnames. With configured host rules, the generated permissions disable unrestricted web fetch/search and provide an allowlisted GET helper. That helper is still not a firewall: shell programs, plugins, symlinks, and subprocesses may bypass the policy. Provider/model API traffic is handled separately. For enforced restrictions, use OS/VM/container isolation and network controls.

## Files written in a configured project

The manager writes or updates `AGENTS.md`, `PROJECT_POLICY.md`, `AGENT_ACCESS_POLICY.json`, and `opencode.json`, and creates `.opencode/` containing the selected agent profiles, team instructions, a manifest, and policy helper tools. It backs up files that it changes. It merges the ordinary JSON object in `opencode.json`; it does not support commented JSONC (`opencode.jsonc`) as input. Existing unrelated/global settings and parent configuration should be reviewed separately.

## Custom agents and tests

Custom English agent profiles are kept in the user's central manager data directory and can be copied to another user's custom-profile directory or included in a separately curated archive. On Windows, central install data is under `%LOCALAPPDATA%\agents-opencode`; on Linux it is under the XDG data directory or `~/.local/share/agents-opencode`.

**Verification status:** the repository includes Python and platform-specific tests. Linux checks have been run, but native Windows installation and end-to-end use have not been verified here; some Windows-specific tests are skipped on Linux. OpenCode behavior and model availability depend on the separately installed local version and providers. No model capability or remote endpoint is certified by this installer.

## Developing this repository: curated Git boundary

This repository can install its own agents without versioning that local
installation. Maintain distributed profiles in `lib/profiles/`, shared
templates and installer logic in `lib/`, and regression tests in `tests/`.
The entry points, `.gitignore` and deliberately maintained product documentation
(such as this README and `START_HAR.md`) also belong in Git.

The root `.gitignore` excludes `.opencode/`, generated root configuration
(`AGENTS.md`, `PROJECT_POLICY.md`, `AGENT_ACCESS_POLICY.json`, `opencode.json`
and `opencode.jsonc`), installer backups and `.local-work/`. Put working notes,
logs, decisions, handoffs and checkpoints in `.local-work/`; do not distribute
them as product documentation. New files elsewhere require explicit review.
These rules apply to this development repository, not automatically to projects
configured by the installer. Ignoring files does not restrict model access.

**First check at every task start or resumption:** inspect `git status --short
--untracked-files=normal`, `git ls-files`, `git ls-files -ci --exclude-standard`
and `git diff --cached --name-status`. Confirm local artifacts are ignored with
`git check-ignore`. If local artifacts are tracked or staged, stop and resolve
the discrepancy without deleting user files. Ignore rules do not untrack files
already in Git, and can be bypassed with `git add -f`.

The ignored local `AGENTS.md` repeats this instruction **outside** the managed
markers, where reinstallation preserves it. On a fresh clone, add that local
instruction when setting up the development agents; it is intentionally not
shipped as part of the installed agent profiles. Before an authorized commit,
review the staged diff and stage only explicit curated paths, never `git add .`
or `git add -A`.
