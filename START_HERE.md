# Start here — OpenCode Agentteam

## Native Windows installation

Requirements: Windows, Python 3.10 or later, Git, and OpenCode installed and configured separately. The installer does not require Bash, administrator rights, Python packages, or a network connection. OpenCode has its own platform requirements and may require Git Bash on Windows; check OpenCode's documentation. That is an OpenCode runtime requirement, not an `install.cmd` requirement.

1. Get the **complete source archive** from GitHub using **Code → Download ZIP**. There is no separate release binary. Extract the complete archive.
2. In Command Prompt, open the extracted folder and run `install.cmd`. To choose a language directly, use `install.cmd --lang en` or `install.cmd --lang sv`. In PowerShell, use `Set-Location` to enter the folder, then run `.\install.cmd`, `.\install.cmd --lang en`, or `.\install.cmd --lang sv`. Choose a language first; Enter selects English.
   To opt out of automatic Windows PATH registration, append `--no-path` to the installer command (for example, `install.cmd --no-path`).
3. In Command Prompt, start `agents-opencode.cmd` from the extracted folder, or run the installed launcher:

   ```text
   "%LOCALAPPDATA%\agents-opencode\bin\agents-opencode.cmd"
   ```

    In PowerShell, run `& "$env:LOCALAPPDATA\agents-opencode\bin\agents-opencode.cmd"`. By default, Windows registers the installed launcher directory in the current user's PATH through HKCU, preserving existing entries and avoiding duplicates; no administrator rights are required. Append `--no-path` to the installer command to opt out. If PATH registration fails, the installer reports an actionable error, but the launcher remains installed and runnable by its full path. PATH updates affect newly started processes, not terminals already open. Open a new terminal; if Windows Terminal or an IDE still has a stale environment, fully restart that parent host or sign out and back in. A Python child process cannot change its parent terminal's environment.
4. Go to a Git project and start the manager. Choose **1** for the full setup wizard. Command Prompt example: `agents-opencode.cmd install --lang sv`. PowerShell example: `.\agents-opencode.cmd install --lang sv`. Interactive runs ask for language first; Enter selects English. Noninteractive runs default to English.

## Linux installation

Extract the complete archive and run `bash install.sh`. Then start `agents-opencode` from a project. Bash is required for this Linux installer; no root privileges or Python packages are needed.

## What the wizard does

The wizard lets you choose agents, models from the separately installed OpenCode command `opencode models`, project data classification, and permissions. No models or API keys are preset. Agent profiles and generated project instructions are in English regardless of the manager UI language.

## Sharing the installer

Share the **complete curated source archive**, for example GitHub's **Code → Download ZIP** archive. There is no separate release ZIP or binary. Do not share a local manager installation or a configured project repository as if it were the installer. Project files such as `opencode.json`, `AGENTS.md`, `PROJECT_POLICY.md`, `AGENT_ACCESS_POLICY.json`, and `.opencode/` are generated locally and are not the curated installer package.

`AGENT_CAST.md` is an optional, fictional and lightly comic presentation of the roles—not real people or relationships. It does not change agent roles, authority, or behavior; humor is optional.

## Security and verification

OpenCode permissions and the access policy are not a sandbox or firewall. Allowed shell commands and programs can use the host account's access. Real restrictions require OS/VM/container controls and network filtering. Read the security sections in `README.md` before granting broad permissions or enabling unattended operation.

The Windows installation is implemented but has not been verified in a native Windows test environment here. Linux checks have been run; some Windows-specific tests are skipped on Linux.
