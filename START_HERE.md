# Start here — install and use the agent team

> Svensk version: [START_HAR.md](START_HAR.md)

This guide is for someone who wants to download the tool from GitHub and get started without already knowing terminal commands. Follow the steps in order. The tool installs an agent team into OpenCode — it does **not** install OpenCode or AI models.

## Step 1 — install the prerequisites

You need Python, OpenCode, and a model OpenCode can use. Git is useful for projects, but **is not required to install this package**. Install programs separately from their official sites:

- [Python — python.org/downloads](https://www.python.org/downloads/) — version 3.10 or later. On Windows, consider selecting the option to add Python to PATH if the installer offers it.
- [Git — git-scm.com/downloads](https://git-scm.com/downloads/) — used for version control. You may decline to create a Git repository in a project.
- [OpenCode — official documentation](https://opencode.ai/docs/) — install OpenCode 1.x and follow its instructions for your computer. Models and model accounts are configured separately in OpenCode. OpenCode may have its own Windows requirements, such as Git Bash; this guide's installer does not require Bash.

**Model accounts and usage may cost money.** Check provider prices and any usage limits before you begin. Seeing a model in the list does not prove that sign-in, billing, or model requests work.

### Open a terminal before entering commands

A **terminal** is a window where you type short text commands instead of clicking buttons. You will open it in a particular folder so the command runs in the right place.

- **Windows:** open a folder in File Explorer. Click the address bar at the top, type `powershell`, and press Enter. A PowerShell window opens in that folder.
- **Linux:** open a folder in your file manager, right-click, and choose something like **Open in Terminal**. The menu name depends on the Linux distribution and file manager. Alternatively, open Terminal from the applications menu and use `cd` to go to the folder.

Type the checks below into the terminal. Press Enter after each line. On Windows:

```powershell
py -3 --version
opencode --version
opencode models
```

On Linux use `python3` instead of `py -3`:

```bash
python3 --version
opencode --version
opencode models
```

The version commands should show installed programs. `opencode models` may contact a provider and needs network access. Seeing a model does not confirm that authentication or usage works. If a command is not recognized, install or configure that program using its official instructions before continuing.

## Step 2 — download and extract the package from GitHub

1. Open the project's GitHub page in your web browser.
2. Click the green **Code** button.
3. Choose **Download ZIP**. Wait for the ZIP file to finish downloading (usually into **Downloads**).
4. Extract the ZIP file — do not run the installer from inside the ZIP.
   - **Windows:** right-click the ZIP file, choose **Extract All…**, then **Extract**.
   - **Linux:** open the ZIP in your file manager and choose **Extract** or **Extract Here**. Wording and location vary by distribution.
5. Open the new extracted folder. It may contain an outer folder with the same name; open the inner package folder. Check that you can see **`install.cmd`** on Windows or **`install.sh`** on Linux. This is the **tool folder**, not your own project.

## Step 3 — install the tool

Install once from the extracted package folder. Keep it distinct from the project folder where you want to use the agents.

### Windows

1. Open the package folder in File Explorer.
2. Click the address bar, type `powershell`, and press Enter. Check that PowerShell opens in the folder where you can see `install.cmd`.
3. Type and run:

   ```powershell
   .\install.cmd --lang en
   ```

   The installer places the launcher under your user profile and normally adds its folder to your user PATH. No administrator rights are needed. If the installer asks for a language, choose English. Open a new terminal window after installation.

### Linux

1. Open the package folder in your file manager.
2. Choose **Open in Terminal** if available. Otherwise open Terminal and use `cd` to go to the package folder.
3. Check that you are in the folder containing `install.sh`, then run:

   ```bash
   bash install.sh --lang en
   ```

   The installer normally places the launcher in `~/.local/bin`. It **does not change your PATH**. This guide therefore uses the launcher's full path, so no terminal configuration is needed. Do not use `sudo`.

## Step 4 — open your project and start configuration

The tool configures a project you already have. If you have a project, use its existing folder. If you only want to try it out, create an empty test folder in your home folder:

- **Windows PowerShell:** `New-Item -ItemType Directory -Force "$HOME\my-first-project" | Out-Null`
- **Linux Terminal:** `mkdir -p "$HOME/my-first-project"`

Now open the **project folder** in File Explorer/file manager, open a terminal there as described in Step 1, and run the command for your system:

**Windows PowerShell:**

```powershell
agents-opencode install --lang en
```

If Windows cannot find the command, invoke the launcher directly:

```powershell
& "$env:LOCALAPPDATA\agents-opencode\bin\agents-opencode.cmd" install --lang en
```

**Linux Terminal** — use the full path; no PATH change is needed:

```bash
"$HOME/.local/bin/agents-opencode" install --lang en
```

If the wizard offers to make the folder a Git project, you can accept `git init` or decline. Git must be installed if you accept. In a folder containing files, agree only if you want Git to start managing the project.

## Step 5 — make choices in the wizard

Take your time and read the questions. To stop without saving the agent configuration, answer no when asked to save. Any folder or Git history you already agreed to create is not removed when you cancel.

1. **Agents:** choose `c` for the suggested core team. That is enough for a first review; you do not need every specialist.
2. **Models:** choose a number from the list loaded with `opencode models`. Seeing a model does not mean your account is signed in or a request will work. Check the provider and price separately. The package includes no model IDs or API keys.
3. **Data classification:** choose based on what information the selected model may see. Choose `PRIVATE` only for verified locally hosted models. Cloud models may receive project instructions and content. `HYBRID` mixes local and cloud use; it does not automatically protect sensitive information.
4. **Permission preset:** choose **1 — Locked-down workstation** for a cautious first try; the initial default is **2**. Read each follow-up question: `ask` means request approval, `deny` means refuse, and `allow` means permit without asking. Leave unattended mode off. Confirm the permission profile with yes when correct, otherwise the wizard stops.
5. Read the summary. When asked whether to save the project configuration and profiles, answer **yes** only if the choices are correct. The default answer to saving is **no**; press Enter for no.

`SHAREABLE` is the classification for information you may share with approved cloud models. If unsure, try only material without secrets or personal data. `PRIVATE` requires verifying that model endpoints really are local, not just choosing a particular model name.

## Step 6 — start the team and give it a first task

Run the start command **from the project folder**.

**Windows PowerShell:**

```powershell
agents-opencode run
```

If the command is not found, use:

```powershell
& "$env:LOCALAPPDATA\agents-opencode\bin\agents-opencode.cmd" run
```

**Linux Terminal:**

```bash
"$HOME/.local/bin/agents-opencode" run
```

When OpenCode opens, enter the task there. A cautious first prompt could be:

> Read the project instructions. Briefly describe what the project does and identify its important files and tests. Do not edit files, install packages, or access the network. Suggest one small next step and wait for my approval.

With the core team selected, orchestrator is already the primary agent; no activation command is needed. Later, add coding and testing roles with `agents-opencode agents` on Windows or `"$HOME/.local/bin/agents-opencode" agents` on Linux if you want the team to write code too. Restart OpenCode after configuration changes. Agent instructions are in English, but you may request replies in your preferred language.

The `resume` and `status` commands also run from the project folder:

**Windows PowerShell:**

```powershell
agents-opencode resume
agents-opencode status
```

**Linux Terminal:**

```bash
"$HOME/.local/bin/agents-opencode" resume
"$HOME/.local/bin/agents-opencode" status
```

## More detail and troubleshooting

- **Model account/pricing:** the model list does not check sign-in or billing. If a request fails, check OpenCode provider settings, your account, and provider pricing.
- **Windows cannot find `agents-opencode`:** open a new terminal window. If it still does not work, use the full launcher path above. OpenCode on Windows may have separate requirements such as Git Bash.
- **Linux cannot find the command:** this guide deliberately uses `"$HOME/.local/bin/agents-opencode"`. The installer does not add `~/.local/bin` to PATH.
- **Git:** Git is separate. The project wizard offers to initialize Git if it is missing; you may decline.
- **JSONC:** the installer handles `opencode.json`, not commented `opencode.jsonc`. Carefully read and merge existing configuration.
- **Windows verification:** native Windows installation and end-to-end use have not been verified here. Linux checks have run; some Windows tests are skipped on Linux.
- **Security:** OpenCode permission rules are not an OS sandbox or firewall. For more about `ask`, `deny`, `allow`, cloud data, and unattended mode, see the security sections in [README.md](README.md).
