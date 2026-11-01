# Börja här – agents-opencode v3 (Go)

Denna guide är skriven för att du ska kunna följa den från början till slut. Programmet installeras en gång per dator; sedan konfigurerar du agentteam **separat i varje projektmapp**.

## 1. Förbered datorn

Installera **Go 1.23+**, **Git** och **OpenCode**. Go behövs bara för att bygga verktyget. Koppla OpenCode till dina valda modeller på vanligt sätt. Kontrollera:

```bash
go version
git --version
opencode --version
opencode models
```

På Fedora kan du installera Go/Git med `sudo dnf install golang git`. På CachyOS/Arch är motsvarigheten `sudo pacman -S go git`.

## 2. Klona och bygg managerprogrammet

```bash
mkdir -p ~/git
cd ~/git
git clone https://github.com/beltet/agents-opencode.git
cd agents-opencode
go test ./...
go build -o agents-opencode ./cmd/agents-opencode
./agents-opencode version
```

Windows: öppna PowerShell i repositorymappen och kör `go test ./...` samt `go build -o agents-opencode.exe ./cmd/agents-opencode`.

## 3. Installera den kompilerade binären

Linux/macOS:

```bash
mkdir -p ~/.local/bin
cp ./agents-opencode ~/.local/bin/agents-opencode
```

Du kan använda `~/.local/bin/agents-opencode` direkt även om mappen inte är på PATH.

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\agents-opencode" | Out-Null
Copy-Item .\agents-opencode.exe "$env:LOCALAPPDATA\agents-opencode\agents-opencode.exe"
```

## 4. Välj ett TESTprojekt innan ditt riktiga

Linux:

```bash
mkdir -p ~/projekt/test-agentteam
cd ~/projekt/test-agentteam
~/.local/bin/agents-opencode install
```

Windows: skapa en tom mapp och kör `& "$env:LOCALAPPDATA\agents-opencode\agents-opencode.exe" install` där.

Installationsguiden frågar i tur och ordning:

1. Agentnummer (se katalogen). Välj uttryckligen själv, exempelvis `3,11,17,23`. Tomt val är inte tillräckligt vid första installationen.
2. Om du vill visa tillgängliga modell-ID:n med `opencode models`.
3. Modell-ID för alla på en gång, eller separat per agent.
4. Om du vill ändra behörigheter och Git-inställningar.
5. Bekräftelse innan projektfilerna skapas.
6. En kort projektbeskrivning. Den kan utökas i `PROJECT_BRIEF.md` senare.

Ingen modell eller extra specialist väljs automatiskt på grund av projektinnehåll. Modeller måste anges av dig.

## 5. Kontrollera resultatet

```bash
~/.local/bin/agents-opencode status
~/.local/bin/agents-opencode doctor
```

Granska `opencode.json`, `.opencode/agents/`, `.agents-opencode/TEAM_REGISTRY.md` och `AGENT_ACCESS_POLICY.json` innan du använder ett riktigt repository. Kör sedan:

```bash
~/.local/bin/agents-opencode run
```

Orkestreraren ska läsa projektbeskrivning och teamregister, notera tillgängliga specialister och delegera programmering, verifiering och granskning till rätt agent när sådan finns.

## 6. Konfigurera Git

Kör `agents-opencode git` för att beskriva Git-läge och ev. remote. **Det gör inte `git push`.** Kör därefter `agents-opencode git-apply` om du vill tillämpa lokal `git config` eller lägga till en ny remote. Vid egen SSH-port används en `ssh://`-URL, t.ex. `ssh://git@server:2222/owner/repo.git`.

## 7. Uppdatera senare

Efter att ha uppdaterat den kompilerade managerbinären måste du uttryckligen öppna respektive projektmapp och köra `agents-opencode refresh`. Programmet visar berörda filer och tar backup före ändringar. Vill du ta manuell backup: `agents-opencode backup`.

## 8. Problem?

`opencode models` fungerar inte: verifiera OpenCode-installation och inloggning; ange modell-ID manuellt om det är känt.

`go` hittas inte: installera en modern Go-version, öppna ny terminal.

`git-apply` säger att remote redan finns med annan adress: det är avsiktligt för att undvika oönskad förändring. Kontrollera `git remote -v` och ändra för hand om du vill.

Behörighetsvarningar: domänlistor, USB och firmware är **inte garanterat blockerade av managerprogrammet**. Läs [docs/SECURITY.md](docs/SECURITY.md).
