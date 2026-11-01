# Byt ut ditt nuvarande `agents-opencode`-repository — säkert, steg för steg

Målet: **behåll Git-historik, remote och GitHub-adressen** `https://github.com/beltet/agents-opencode`, men byt alla spårade Python-installationsfiler mot den nya Go-koden. Kör på din utvecklingsdator, helst Fedora/CachyOS. Guiden använder Bash-liknande kommandon; den fungerar i Fish där det inte anges något annat.

> Du får ett källkodsarkiv med den nya applikationen från ChatGPT. Detta är **inte** en ändring som redan utförts i ditt GitHub-repository. Inga Git-pushar har utförts från ChatGPT.

## Steg 1 — Kontrollera befintligt repository

```bash
cd ~/git/agents-opencode
git status --short
git remote -v
git branch --show-current
```

**Om `git status --short` visar ändringar: stanna och spara dem manuellt (commit eller `git stash`) innan du fortsätter.** Ersätt inte ett repository med ocommittad data.

## Steg 2 — Ta en full lokal säkerhetskopia

```bash
cd ~/git
cp -a agents-opencode agents-opencode-backup-before-go
```

Denna katalog innehåller även dess `.git` och gör det möjligt att backa ut även om något går fel. Gör **inte** backupen i själva repositorymappen.

## Steg 3 — Skapa en separat arbetsgren

```bash
cd ~/git/agents-opencode
git switch main
git pull --ff-only origin main
git switch -c rewrite/go-v3
```

Om `main` inte är din standardgren, använd den faktiska gren som visas via `git branch -a`.

## Steg 4 — Packa upp det nya källkodsarkivet

Ladda ner `agents-opencode-go-rewrite.zip` från ChatGPT och lägg det i `~/Downloads`.

```bash
mkdir -p ~/Downloads/agents-opencode-go-import
unzip -o ~/Downloads/agents-opencode-go-rewrite.zip -d ~/Downloads/agents-opencode-go-import
ls ~/Downloads/agents-opencode-go-import/agents-opencode-rewrite
```

Du bör se `go.mod`, `README.md`, `cmd/`, `internal/`, `assets/`, `docs/` osv.

## Steg 5 — Ersätt gamla spårade filer

**OBS: Bara på den nya arbetsgrenen, efter backup!**

```bash
cd ~/git/agents-opencode
git rm -r -- .
cp -a ~/Downloads/agents-opencode-go-import/agents-opencode-rewrite/. .
```

`git rm -r -- .` tar bort spårade filer ur arbetskopian och markerar dem för borttagning. Den rör inte din `.git`-historik. Med `cp -a` lägger du in de nya filerna. Kontrollera att du verkligen står i `~/git/agents-opencode`.

Gamla **ospårade** filer kan finnas kvar. Kontrollera dem med `git status --short`. Kör inte `git clean -fdx` blint.

## Steg 6 — Bygg och testa

På Fedora:

```bash
sudo dnf install golang git
```

På CachyOS/Arch:

```bash
sudo pacman -S go git
```

Därefter:

```bash
cd ~/git/agents-opencode
go version
go test ./...
go vet ./...
go build -o agents-opencode ./cmd/agents-opencode
./agents-opencode version
./agents-opencode catalog
```

Testa gärna konfigurationen först i en tom mapp, **inte ditt viktiga RDEV-repository**:

```bash
mkdir -p ~/agentteam-test
cd ~/agentteam-test
~/git/agents-opencode/agents-opencode install
~/git/agents-opencode/agents-opencode doctor
```

## Steg 7 — Granska vad som ska läggas upp

Tillbaka i källkodsrepositoryt:

```bash
cd ~/git/agents-opencode
git status --short
```

Lägg bara till de **avsedda källkods- och dokumentationskatalogerna**. Lägg inte till en genererad `.opencode`, projektdata, hemligheter, lokala backuper eller binärfiler.

```bash
git add README.md START_HAR.md START_HERE.md go.mod .gitignore cmd internal assets docs scripts .github

git diff --cached --stat
git diff --cached --check
git status --short
```

De gamla spårade filerna är redan markerade som borttagna i steg 5. De nya filerna är explicit tillagda ovan.

Om `git status --short` visar oväntade känsliga filer som är staged, stoppa och kör `git restore --staged -- <fil>` för att avmarkera dem.

## Steg 8 — Commit och push till en ny gren

```bash
git commit -m "Rewrite agents-opencode as native Go manager"
git push -u origin rewrite/go-v3
```

Du får nu en ny gren på samma GitHub-repository. GitHub Actions kan köra tester och bygga releaser om workflows är aktiverade.

## Steg 9 — Publicera på `main`

Öppna GitHub och skapa en Pull Request från `rewrite/go-v3` till `main`. Granska ändringarna och CI-resultaten. Slå ihop när du är nöjd.

Vill du i stället göra en lokal fast-forward efter att alla ändringar granskats:

```bash
git switch main
git pull --ff-only origin main
git merge --ff-only rewrite/go-v3
git push origin main
```

**Gör detta endast om main inte har divergerat, du har rätt push-behörighet och du medvetet vill ersätta main.** Använd aldrig force push som genväg.

## Steg 10 — Installera binären på din dator

```bash
cd ~/git/agents-opencode
go build -o agents-opencode ./cmd/agents-opencode
mkdir -p ~/.local/bin
cp ./agents-opencode ~/.local/bin/agents-opencode
~/.local/bin/agents-opencode version
```

När programmet uppdaterats kan du köra `agents-opencode migrate` i en **kopia** av ett gammalt OpenCode-projekt, och därefter ett uttryckligt `refresh` i riktiga projekt när du granskat resultatet.

## Ångra omskrivningen

Den gamla koden finns kvar i Git-historiken, på `main` om PR ännu inte mergats, och i `~/git/agents-opencode-backup-before-go`. Du kan helt enkelt byta tillbaka till `main` före PR, eller återställa filerna från säkerhetskopian. Om du redan mergat, använd en ny revert-commit i stället för force push.
