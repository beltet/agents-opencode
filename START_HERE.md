# Start here: agents-opencode Go rewrite

1. Install Go 1.23+, Git, and OpenCode separately. Connect your models in OpenCode.
2. Clone the repository and build the native executable:

```bash
git clone https://github.com/beltet/agents-opencode.git
cd agents-opencode
go test ./...
go build -o agents-opencode ./cmd/agents-opencode
```

3. On Linux/macOS copy the binary into `~/.local/bin`; on Windows build with `.exe` extension and copy it into `%LOCALAPPDATA%\agents-opencode`.
4. Enter a **separate** test project directory and run `agents-opencode install`.
5. Choose agents and model IDs **manually**. Optionally configure permissions and Git. Confirm file changes, then describe the new project in `PROJECT_BRIEF.md`.
6. Inspect `agents-opencode status` and `agents-opencode doctor`, then start `agents-opencode run`.
7. For an older project, test `agents-opencode migrate` on a copy first. `refresh` updates managed files with backups.

Security warning: OpenCode tool permissions are not a firewall, filesystem sandbox, Git remote guard, or firmware/USB control system. Read [docs/SECURITY.md](docs/SECURITY.md).

The interactive beta UI is predominantly English; the generated agent prompts remain English. No models or specialists are chosen automatically. The software was built and tested on Linux and cross-compiled for other platforms, but live OpenCode integration has not been verified in this delivery environment.
