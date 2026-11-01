# agents-opencode — Go rewrite (3.0.0-beta.1)

**Manuell, projektlokal hantering av OpenCode-agentteam.** Den tidigare Python-installationsapplikationen har skrivits om från grunden i Go. **Användaren väljer alla agenter, modeller och behörigheter; programmet analyserar inte projektet och väljer ingenting automatiskt.** Orkestreraren anpassar uppgiftsfördelningen efter de installerade specialisterna.

> **Status: beta.** Källkoden har byggts och testats med Go på Linux. Windows/macOS kan korskompileras och testas i GitHub Actions, men ett faktiskt installerat OpenCode och anslutna modeller har **inte** testats i den här leveransmiljön. Granska och testa på en separat projektmapp innan du migrerar dina riktiga projekt.

**[Svensk steg-för-steg-guide](START_HAR.md)** · **[English getting started](START_HERE.md)** · [Säkerhetsbegränsningar](docs/SECURITY.md) · [GitHub-utbyte](docs/BYT_UT_GITHUB_PROJEKTET.md)

## Vad ingår?

- En Go-binär (`agents-opencode`) utan Pythonberoende vid körning, med 23 inbäddade specialistprofiler som utgångspunkt.
- Manuell agentlista, manuellt modellval per agent och valfri bulk-tilldelning. Modellnamn kan listas med `opencode models`, som hanteras av en separat installerad OpenCode.
- En enkel projektbeskrivning i `PROJECT_BRIEF.md` som **orkestreraren** använder, inte installationsprogrammet.
- Projektlokal manifest- och teamregistrering, OpenCode-konfiguration, instruktioner och behörighetspolicy.
- Separata behörighetsfält för verktyg, Git, internet/domäner, lokala sökvägar, nätverksdiskar, USB och firmware samt per-agent-undantag.
- Git-konfiguration: lokalt, befintligt repo eller remote, författare/e-post och SSH-port/adress. Ändringar av faktisk Git-konfiguration kräver ett separat, uttryckligen bekräftat `git-apply`.
- Säkerhetskopior av ändrade filer, idempotent refresh, installerarens diagnostik och importer av äldre agentmanifest.
- Körläge `run` eller `resume` startar separat installerad OpenCode.
- Standardbiblioteket i Go; inga externa Go-paket.

## Krävs

- **För att bygga:** Go 1.23 eller senare (under build, inte när binären körs).
- **För att använda agenter:** OpenCode separat installerat och konfigurerat med dina modeller.
- **För Git-funktioner:** Git samt fungerande SSH-klient/nycklar om SSH används.

## Snabbstart på Linux/macOS

```bash
# Kör i det här källkodsrepositoryt:
go test ./...
go build -o agents-opencode ./cmd/agents-opencode

# Installera binären för din användare:
mkdir -p "$HOME/.local/bin"
cp agents-opencode "$HOME/.local/bin/agents-opencode"

# Gå till en annan projektmapp (den du vill bygga):
mkdir -p "$HOME/projekt/testprojekt"
cd "$HOME/projekt/testprojekt"
"$HOME/.local/bin/agents-opencode" install
```

Du väljer agenter och modell-ID:n manuellt i guiden. Ange modell-ID exakt så som OpenCode visar (t.ex. via `opencode models`). Vissa modeller kan vara listade trots saknad inloggning. Inga betalmodeller väljs automatiskt. Välj gärna en *testmapp* första gången.

Starta OpenCode i samma projekt:

```bash
agents-opencode status
agents-opencode doctor
agents-opencode run
# Fortsätt en tidigare OpenCode-session:
agents-opencode resume
```

Om `~/.local/bin` inte ligger på PATH, använd den fullständiga sökvägen.

## Snabbstart Windows (PowerShell)

```powershell
go test ./...
go build -o agents-opencode.exe ./cmd/agents-opencode
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\agents-opencode" | Out-Null
Copy-Item .\agents-opencode.exe "$env:LOCALAPPDATA\agents-opencode\agents-opencode.exe"
New-Item -ItemType Directory -Force "$HOME\Projects\TestProjekt" | Out-Null
Set-Location "$HOME\Projects\TestProjekt"
& "$env:LOCALAPPDATA\agents-opencode\agents-opencode.exe" install
```

Starta om terminalen om du ändrar PATH. Binären installerar inte OpenCode, Git eller SSH åt dig.

## Kommandon

| Kommando | Funktion |
|---|---|
| `agents-opencode` | Enkel huvudmeny |
| `install [mapp]` / `configure` | Skapa eller ändra projektteam interaktivt |
| `agents` | Välj installerade agentroller manuellt |
| `models` | Välj modell per agent manuellt |
| `list-models` | Visa modell-ID:n från `opencode models` |
| `catalog` | Visa de 23 inbyggda rollerna |
| `permissions` / `access` / `hardware` | Behörighetsinställningar |
| `git` | Spara Git/SSH-intentioner i projektkonfigurationen |
| `git-apply` | Begär bekräftelse och tillämpa begränsade `git config` / `git remote add`-ändringar |
| `status` | Visa valda roller, modeller och projektläge |
| `doctor` / `audit` | Konfigurationskontroller och säkerhetsvarningar |
| `refresh` | Förnya genererade filer, med förhandsvisning och backup |
| `migrate` | Läs äldre `.opencode/agentteam-manifest.json`, importera roller/modeller |
| `backup` | Skapa manuell projektbackup |
| `restore --from=<katalog>` | Återställ en tidigare managerbackup efter bekräftelse |
| `run` / `resume` | Starta OpenCode / återuppta session |
| `version` | Visa manager-version |

Ange en projektmapp som sista argument eller `--project=/sökväg/till/projekt`. Flaggan `--dry-run` visar ändringar utan att skriva dem. `--lang=sv` / `--lang=en` är reserverade för språkinställning; den nuvarande betaversionens interaktiva menyer är främst på engelska.

### Egna agenter

Skapa `.agents-opencode/custom/min-agent.md` i projektet. Skriv instruktioner på engelska och välj `min-agent` som namn i agentlistan. Installeraren kopierar dess instruktioner till `.opencode/agents/`. Egna agenters exakta instruktioner och modeller väljs av användaren.

## Genererade filer i ett projekt

```text
PROJECT_BRIEF.md                   # Beställarens projektbeskrivning
AGENTS.md                          # Ett avgränsat, managergenererat avsnitt
AGENT_ACCESS_POLICY.json          # Användarens avsikter och policy
opencode.json                      # Projektets OpenCode-inställningar (befintliga övriga nycklar bevaras)
.agents-opencode/
  config.json                      # Managerens projektkonfiguration
  TEAM_REGISTRY.md                 # Installerade agentroller och manuella modellval
  backups/<UTC-tid>/               # Säkerhetskopior före ändring
  custom/*.md                      # Valfria egna agentmallar
.opencode/
  agents/*.md                      # Endast valda profiler
  team/*.md                        # Gemensamma arbetsregler
```

Användarägda delar av `AGENTS.md` och orelaterade nycklar i giltig `opencode.json` bevaras. Filer med kommentarer (`JSONC`) i `opencode.json` avvisas i betaversionen i stället för att skrivas över. **Backuper läggs lokalt i projektet.** Granska deras Git-status innan du publicerar något.

### Behörigheter — viktigt att känna till

Det här programmet är **inte en säkerhetssandbox**. OpenCode kan tillämpa verktygsbehörigheter, men tillåten `bash`, `ssh`, shell-skript, plugins och underprocesser kan kringgå vissa avsiktsbaserade begränsningar. URL-/domänlistor, USB-ID:n, nätverksdiskar, firmware och remote-/grenbegränsningar finns i policyfilen för agenternas instruktioner men genomdriver **inte** en värdsystembaserad åtkomstkontroll. Firmware-kommandon spärras konservativt via kända kommandomönster. För verklig isolering behövs användarkonton/ACL, VM/container, brandvägg, SSH-serverns rättigheter och/eller hårdvarubegränsningar. Se [docs/SECURITY.md](docs/SECURITY.md).

`--auto` vid `Unattended` kan godkänna `ask` automatiskt. Sätt `deny` för det som **måste** förbli otillåtet. En Git-push-behörighet i ett verktygsfilter är aldrig en garanti att kommandot inte kan riktas mot en annan remote via en alternativ shellväg.

## Git och SSH

För egen SSH-port, använd en fullständig remote-URL, exempelvis:

```text
ssh://git@192.0.2.10:2222/team/myproject.git
```

`git`-menyn sparar en *avsedd konfiguration*. Kör `agents-opencode git-apply` separat för att göra godkända lokala ändringar. `git-apply` ändrar inte SSH-nycklar, host key verifiering, serverinställningar, befintliga remoters URL:er eller Git-branch som standard. Det gör inga pushar. Kommandot `git push` behöver alltid godkännas inom projektets regler.

## Befintliga projekt / migrering

**Testa på en kopia först.** Om ett projekt har gammalt `.opencode/agentteam-manifest.json`, välj `agents-opencode migrate`. Importen läser de 23 agentnamnen och nuvarande modellval, men använder konservativa behörighetsstandarder i stället för att ärva alltför öppna gamla rättigheter. Du får en förhandsvisning innan ändring. Befintliga projektfiler som ändras backas upp.

Den här omskrivningen av managerprogrammet ändrar **inte** användarens Git-repository eller gamla projekt automatiskt. Varje projekt uppdateras bara när du kör ett uttryckligt kommando i den projektmappen.

## Testning och byggen

```bash
go test ./...
go vet ./...
go build ./cmd/agents-opencode
```

Bygg för andra operativsystem (korskompilering, inte samma sak som körtest):

```bash
GOOS=windows GOARCH=amd64 go build -o agents-opencode-windows-amd64.exe ./cmd/agents-opencode
GOOS=darwin GOARCH=arm64 go build -o agents-opencode-macos-arm64 ./cmd/agents-opencode
GOOS=linux GOARCH=arm64 go build -o agents-opencode-linux-arm64 ./cmd/agents-opencode
```

GitHub Actions testar Go-kod på Windows, Linux och macOS och skapar artefakter/releaser via `.github/workflows/` när repositoryt har pushats. **Säg inte att OpenCode-integration fungerar förrän den testats med verklig installation och modell.**

## Nuvarande begränsningar i betaversionen

1. Ingen Live/OpenCode-integrationstestning har utförts här (ingen installerad OpenCode i byggmiljön).
2. Primär JSON-kodgenerering följer dokumenterat OpenCode **1.x**-schema. Okända framtida format och 2.x verifieras inte automatiskt och ska inte antas vara kompatibla.
3. Interaktiva menyer är för närvarande huvudsakligen på engelska, trots att svensk dokumentation finns.
4. Försöker inte implementera en OS-brandvägg, USB-policy enforcement eller fullständig shell-sandbox.
5. Git `SSHIdentity` lagras bara som sökvägsmetadata; SSH-config/agent hanteras separat.
6. Interaktiv guide är textbaserad och inte en fullskalig grafisk TUI. Ingen modellbenchmark, automatisk projektanalys eller modelldispatch ingår avsiktligt.
7. Installeraren gör backup men har inte full transaktionell rollback över en hel uppsättning filer vid strömavbrott mitt i installation; tidigare filer kan återställas från backup.

## Licens

Bevara den licens som gäller för originalprojektet om en sådan finns; denna leverans tilldelar ingen ny licens åt tredjeparts- eller tidigare projektmaterial.
