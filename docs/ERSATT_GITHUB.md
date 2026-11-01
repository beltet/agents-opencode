# Byt från gamla agents-opencode till GUI-versionen

Dessa steg ersätter innehållet på en **ny Git-gren**, men bevarar Git-historiken och ger dig möjlighet att granska allt innan merge till `main`.

## 1. Hämta GUI-källkoden

Ladda ned `agents-opencode-qt6-gui-source.zip` och lägg den i `~/Downloads`.

```bash
cd ~/Downloads
unzip agents-opencode-qt6-gui-source.zip
```

Det skapar katalogen `agents-opencode-qt6-gui/`.

## 2. Spara ditt befintliga projekt

```bash
cd ~/git/agents-opencode
git status --short
```

**Stanna om du har ocommittade ändringar** – committa eller spara dem separat först. Därefter:

```bash
cd ~/git
cp -a agents-opencode agents-opencode-backup-before-gui
cd agents-opencode
git switch main
git pull --ff-only origin main
git switch -c rewrite/qt6-gui
```

## 3. Ersätt den gamla programkoden

```bash
# Kontrollera först att du är på rewrite/qt6-gui och att status är ren.
git status --short
git branch --show-current

# Ta bort de gamla SPÅRADE programfilerna (inte .git-historiken).
git rm -r -- .

# Kopiera in hela den nya källkoden, inklusive .github/.
cp -a ~/Downloads/agents-opencode-qt6-gui/. .
```

Kontrollera med:

```bash
git status --short
git diff --stat
```

## 4. Bygg och testa på Fedora

```bash
sudo dnf install cmake ninja-build gcc-c++ qt6-qtbase-devel git
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel "$(nproc)"
ctest --test-dir build --output-on-failure
./build/agents-opencode
```

På CachyOS/Arch: `sudo pacman -S --needed cmake ninja gcc qt6-base git`.

Öppna programmet, välj **en tom testmapp** som projekt och prova att välja två agenter och modeller. Kontrollera genererad `opencode.json` innan du använder din riktiga utvecklingsmapp.

## 5. Pusha nya grenen

```bash
git add -A
git diff --cached --check
git diff --cached --stat
git commit -m "Rewrite agents-opencode as Qt6 desktop GUI"
git push -u origin rewrite/qt6-gui
```

Öppna GitHub och skapa en Pull Request från `rewrite/qt6-gui` till `main`. Då körs bygg- och testflödet från `.github/workflows/build-and-release.yml`.

**Viktigt:** CI har inte körts av mig. Granska eventuella byggfel och lös dem innan merge. Denna guide påstår inte att fyra plattformsbinärer redan är publicerade.

## 6. Publicera färdiga binärer på GitHub

Efter att Pull Requesten har blivit granskad och mergad till `main`:

```bash
git switch main
git pull --ff-only origin main
git tag v3.1.0-beta.1
git push origin v3.1.0-beta.1
```

GitHub Actions försöker då kompilera och paketera Windows, Linux och macOS. Om alla byggen lyckas publiceras de automatiskt under GitHub **Releases** som en beta. Om byggen misslyckas skapas ingen komplett release – titta under **Actions** för felsökningsloggar.

Efter en vanlig push till `main` kan du också ladda ner testade binärpaket under **Actions → Artifacts** utan att skapa en release.

## 7. Flytta inte agentinställningar i onödan

Den nya GUI-appen ska köras i varje projekts egen mapp. Testa den först i en kopia av ett gammalt projekt. Den skriver inte om gamla projekts agentkonfigurationer bara för att du installerar eller bygger managerappen.

Ändra inte gamla konfigurationsfiler manuellt förrän du har backup och har läst GUI:ts förhandsgranskning.
