# Agents OpenCode GUI

**En liten grafisk skrivbordsapplikation för att installera och konfigurera OpenCode-agentteam.**

En ny C++20/Qt 6 Widgets-implementering. Inga terminalmenyer, ingen webbläsare, ingen lokal webbtjänst och inget Go/Python-körberoende. Programmet analyserar inte projektet, rekommenderar inte agenter och väljer inte AI-modeller åt dig.

> **Status: 3.1.0-beta.1 / källkodsprototyp.** GUI-källkoden och automatiska projektkonfigurationstester ingår. Qt-utvecklingsmiljön finns inte i leveranscontainern, så Qt-versionen har **inte kunnat kompileras eller körtestas här**. GitHub Actions bygg-/testflöde med paketering för Windows, Linux och macOS ingår men ska verifieras när du pushat. Testa alltid i en separat projektmapp först. De tidigare Go-binärerna är inte denna GUI-version.

## Hur ser programmet ut?

Ett normalt skrivbordsfönster med fem flikar:

1. **Projekt:** välj en mapp och skriv projektbeskrivningen.
2. **Agenter och modeller:** bocka i vilka av 23 agentroller du vill ha, välj modell per agent i redigerbara listor. Hämta modell-ID:n från `opencode models` om tillgängligt. Bulkmodellval finns.
3. **Behörigheter:** välj Tillåt / Fråga / Neka för verktyg och Git, ange tillåtna eller spärrade internetadresser, lokala sökvägar, nätverksdiskar, USB-enheter och firmwareåtkomst. Även enkla per-agent-undantag.
4. **Git / SSH:** lokal Git eller remote, SSH-värd och port, SSH-användare, referens till privat nyckel, repository, författarnamn och e-post. Separat knapp för att *efter bekräftelse* göra godkända lokala Git-ändringar.
5. **Förhandsgranska:** se genererad OpenCode-konfiguration före installation.

**Spara och installera agentteam** skriver projektfilerna och säkerhetskopierar befintliga hanterade filer. Programmet utför aldrig `git push` automatiskt.

### För vilka OpenCode-versioner?

Denna beta genererar det dokumenterade **OpenCode 1.x-konfigurationsformatet** (`agent`, `permission`, `bash`, `task`). Den stoppar installation vid detekterad OpenCode 2.x och nekar att skriva över en identifierad V2-konfiguration. V2 kräver en separat adapter och är *inte* implementerad ännu.

## Kom igång med färdiga binärer från GitHub

När källkoden finns på GitHub och Actions-byggena fungerar hittar du automatiskt skapade filer här:

- **Actions → Build GUI binaries → senaste lyckade körning → Artifacts.** Finns på push till `main` och på manuella arbetsflödeskörningar.
- **Releases** efter att du har pushat en versionstagg som börjar med `v`, exempelvis `v3.1.0-beta.1`.

De avsedda releaseformaten är:

| Operativsystem | Paket | Användning |
|---|---|---|
| Linux x86_64 | `.AppImage` | Gör körbar, dubbelklicka |
| Windows x86_64 | `.zip` med `.exe` och Qt-bibliotek | Packa upp och starta `.exe` |
| macOS Intel | `.dmg` med `.app` | Öppna `.dmg`, flytta appen till Applications |
| macOS Apple Silicon | `.dmg` med `.app` | Samma som ovan |

**OBS:** Dessa binärer finns inte automatiskt på GitHub innan koden har pushats och GitHub Actions har byggt dem. Osignerade Windows- och macOS-program kan utlösa plattformarnas säkerhetsvarningar. Linux AppImage kräver en kompatibel Linuxmiljö och kan kräva `libfuse2`/FUSE-stöd på vissa distributioner.

## Bygga från källkod

Du behöver Git, CMake 3.21+, en C++20-kompilator samt Qt **6.5+** (Core, Widgets och Test). CMake bygger två program: skrivbordsapplikationen och automatiska tester.

### Fedora (inklusive utvecklingsmaskinen)

```bash
sudo dnf install cmake ninja-build gcc-c++ qt6-qtbase-devel git
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel "$(nproc)"
ctest --test-dir build --output-on-failure
./build/agents-opencode
```

### CachyOS / Arch Linux

```bash
sudo pacman -S --needed cmake ninja gcc qt6-base git
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel "$(nproc)"
ctest --test-dir build --output-on-failure
./build/agents-opencode
```

### Windows

Installera Qt 6 (inklusive Qt Widgets och den kit som matchar MSVC), CMake och Visual Studio 2022 C++ build tools. Öppna en terminal med korrekt byggmiljö, eller använd **Qt Creator**, öppna `CMakeLists.txt`, välj Qt 6 kit och tryck Build/Run. För ett delbart paket används `windeployqt` (GitHub Actions sköter detta automatiskt).

### macOS

Installera Xcode Command Line Tools, CMake och Qt 6. Öppna projektet i Qt Creator och bygg det, eller kör:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
open build/agents-opencode.app
```

GitHub Actions använder `macdeployqt` för att skapa delbara `.dmg`-paket.

## Så använder du GUI:t

1. Öppna applikationen och välj den projektmapp där du senare kör OpenCode.
2. Gå till **Projekt** och beskriv vad du vill att agenterna ska utveckla.
3. Under **Agenter och modeller**, välj dina experter och ange exakt modell-ID (`provider/model`). Orkestreraren krävs. Ingen AI-tjänst kontaktas bara för att konfigurera teamet, med undantag av frivillig lokal `opencode models`-hämtning.
4. Konfigurera behörigheter. Lämna `USB` och `Firmwareflashning` på **Neka** tills du verkligen behöver dem.
5. Välj Git-läge, adress, SSH-port, identitet och författare. Behåll dina befintliga SSH-nycklar. Den privata nyckeln kopieras inte av programmet.
6. Klicka på **Visa ändringar**, läs igenom, och klicka sedan **Spara och installera agentteam**.
7. Vill du tillämpa lokala Git-inställningar, använd knappen på Git-fliken. Inget pushas.
8. Öppna en terminal **i projektmappen** och starta `opencode` som vanligt. Orkestreraren läser `PROJECT_BRIEF.md` och teamregistret.

### Skapade filer

```text
PROJECT_BRIEF.md                Projektbeskrivning som orkestreraren läser
AGENTS.md                       Ett avgränsat, automatiskt teamavsnitt
opencode.json                   OpenCode 1.x-agentinställningar
AGENT_ACCESS_POLICY.json       Avsiktsregler för åtkomst och hårdvara
.agents-opencode/
  config.json                   Projektets valda agenter, modeller, regler, Git
  TEAM_REGISTRY.md              Inventering för orkestreraren
  backups/...                   Kopior av tidigare hanterade filer
.opencode/
  agents/*.md                   Valda specialistprofiler
  team/*.md                     Gemensamma arbets- och säkerhetsregler
```

Den inbyggda orkestreraren kontrollerar det faktiska teamet vid start/återupptagning och ska logga sitt uppdrag och kompetensluckor i `.local-work/ACTIVE.md`. Installationsprogrammet gör ingen automatisk projektanalys.

## Viktigt om säkerhet och behörigheter

**Detta är inte en OS-sandbox.** `AGENT_ACCESS_POLICY.json` lagrar även regler som inte kan upprätthållas fullt ut av OpenCode 1.x. Exempel: exakt URL-/domänfilter, specifika USB-enheter, firmwareflashning och tillåtna Git-remotes/grenar. Fri shellåtkomst kan kringgå rådgivande regler. Välj Neka för otillåtna verktyg, använd en begränsad OS-användare/VM/brandvägg där stark isolering behövs och ge inte obevakat läge till ett team utan genomgång.

För Git gäller: SSH-nyckeln pekas endast ut som en sökväg, den kopieras inte och git-konfigurationsknappen skriver inte automatiskt `core.sshCommand`. SSH-porten ingår i nya SSH-URL:er som programmet kan lägga till. Befintliga remotes ändras inte automatiskt.

## Om projektets status och testning

- Innehåller 23 inbäddade agentprofiler samt gemensamma regler.
- Innehåller C++/Qt-test för profiles, save/load, preservation, bortvalda agenter, kodgranskarens skrivskydd och symlänkvägran.
- Innehåller GitHub Actions med fyra plattformsmatriser och releasepublicering när en tagg pushas.
- **Inte verifierat med lokal Qt-kompilering eller riktig OpenCode-session i denna miljö.** CI-status måste kontrolleras innan du använder paket i skarpa projekt.
- Egna anpassade agentprofiler och OpenCode 2.x-adapter är inte implementerade i denna beta.

## Dokumentation

- [Starta här – kort nybörjarguide](START_HAR.md)
- [Tredjepartslicenser](THIRD_PARTY_NOTICES.md)

- [Ersätt tidigare repository och pusha säkert](docs/ERSATT_GITHUB.md)
- [Säkerhetsgränser](docs/SAKERHET.md)
- [Officiell Qt-dokumentation](https://doc.qt.io/qt-6/)
- [OpenCode permissions](https://docs.opencode.ai/docs/permissions/)

**Qt-licens:** Qt tillhandahålls under olika licenser, bland annat LGPLv3 för tillämpliga moduler under gällande villkor. Om du distribuerar binärer måste du uppfylla Qt:s licenskrav och inkludera lämpliga notifieringar, licenstexter och eventuellt återlänkningsmöjligheter. Projektets egen licens måste fastställas av repositoryägaren.
