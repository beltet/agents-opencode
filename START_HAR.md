# Börja här — installera och använd agentteamet

> English version: [START_HERE.md](START_HERE.md)

Den här guiden är för dig som vill hämta verktyget från GitHub och börja använda det utan att kunna terminalkommandon sedan tidigare. Följ stegen i ordning. Verktyget installerar ett agentteam i OpenCode — det installerar **inte** OpenCode eller AI-modeller.

## Steg 1 — installera förberedelserna

Du behöver Python, OpenCode och en modell som OpenCode kan använda. Git är användbart för projekt, men **krävs inte för att installera paketet**. Installera programmen separat från deras officiella sidor:

- [Python — python.org/downloads](https://www.python.org/downloads/) — version 3.10 eller senare. På Windows, markera gärna alternativet att lägga till Python i PATH om installationsprogrammet erbjuder det.
- [Git — git-scm.com/downloads](https://git-scm.com/downloads/) — behövs för versionshantering. Du kan tacka nej till att skapa ett Git-repository i ett projekt.
- [OpenCode — officiell dokumentation](https://opencode.ai/docs/) — installera OpenCode 1.x och följ dokumentationen för din dator. Modeller och modellkonton ställs in i OpenCode separat. OpenCode kan ha egna plattformskrav på Windows, exempelvis Git Bash; installationsprogrammet i den här guiden kräver inte Bash.

**Modellkonton och användning kan kosta pengar.** Kontrollera providerpriser och eventuella användningsgränser innan du börjar. Att en modell visas i listan är inte bevis för att inloggning, betalning eller anrop fungerar.

### Öppna en terminal innan du skriver kommandon

En **terminal** är ett fönster där du skriver korta textkommandon i stället för att klicka på knappar. Du kommer att öppna den i en viss mapp, så att kommandot körs på rätt plats.

- **Windows:** öppna mappen i Utforskaren. Klicka i adressfältet högst upp, skriv `powershell` och tryck Enter. Ett PowerShell-fönster öppnas i den mappen.
- **Linux:** öppna mappen i filhanteraren, högerklicka och välj exempelvis **Open in Terminal** / **Öppna i terminal**. Menynamnet beror på Linux-distribution och filhanterare. Alternativt öppnar du Terminal från programmenyn och använder `cd` för att gå till mappen.

Skriv inledande kontrollkommandon i terminalen. Tryck Enter efter varje rad. På Windows:

```powershell
py -3 --version
opencode --version
opencode models
```

På Linux används `python3` i stället för `py -3`:

```bash
python3 --version
opencode --version
opencode models
```

Versionskommandona ska visa installerade program. `opencode models` kan kontakta en provider och kräver nätverk. En visad modell bekräftar inte att autentisering eller användning fungerar. Om något kommando inte känns igen, installera eller konfigurera motsvarande program enligt dess officiella instruktioner innan du fortsätter.

## Steg 2 — hämta och packa upp paketet från GitHub

1. Öppna projektets GitHub-sida i webbläsaren.
2. Klicka på den gröna knappen **Code**.
3. Välj **Download ZIP**. Vänta tills ZIP-filen har hämtats till datorn (oftast mappen **Nedladdningar / Downloads**).
4. Packa upp ZIP-filen — kör inte installationsprogrammet inuti ZIP-filen.
   - **Windows:** högerklicka på ZIP-filen och välj **Extract All… / Extrahera alla…**, sedan **Extract / Extrahera**.
   - **Linux:** öppna ZIP-filen i filhanteraren och välj **Extract / Extrahera** eller **Extract Here / Extrahera här**. Namn och placering kan skilja sig mellan distributioner.
5. Öppna den nya, uppackade mappen. Den kan innehålla en yttre mapp med samma namn; öppna den inre paketmappen. Kontrollera att du ser filen **`install.cmd`** på Windows eller **`install.sh`** på Linux. Den här mappen är **verktygsmappen**, inte ditt eget projekt.

## Steg 3 — installera verktyget

Installationen görs en gång från paketmappen du just packade upp. Håll isär den mappen och projektmappen där du vill använda agenterna.

### Windows

1. Öppna paketmappen i Utforskaren.
2. Klicka i adressfältet, skriv `powershell` och tryck Enter. Kontrollera att PowerShell öppnas i mappen där du ser `install.cmd`.
3. Skriv och kör:

   ```powershell
   .\install.cmd --lang sv
   ```

   Installationen placerar launchern under din användarprofil och lägger normalt dess katalog till användarens PATH. Du behöver inte administratörsrättigheter. Om terminalen ber om språk kan du välja svenska. Öppna ett nytt terminalfönster efter installationen.

### Linux

1. Öppna paketmappen i filhanteraren.
2. Välj **Open in Terminal / Öppna i terminal** om alternativet finns. Annars öppnar du Terminal och går till paketmappen med `cd`.
3. Kontrollera att du är i mappen där `install.sh` syns, och kör:

   ```bash
   bash install.sh --lang sv
   ```

   Installationen placerar normalt launchern i `~/.local/bin`. Den **ändrar inte din PATH**. Därför använder den här guiden launcherns fullständiga sökväg, så du behöver inte ändra terminalinställningar. Kör inte `sudo`.

## Steg 4 — öppna ditt projekt och starta konfigurationen

Verktyget konfigurerar ett projekt som du redan har. Om du har ett projekt, använd dess befintliga mapp. Om du bara vill prova kan du skapa en tom testmapp i din hemmapp:

- **Windows PowerShell:** `New-Item -ItemType Directory -Force "$HOME\my-first-project" | Out-Null`
- **Linux Terminal:** `mkdir -p "$HOME/my-first-project"`

Öppna sedan **projektmappen** i Utforskaren/filhanteraren, öppna en terminal där enligt instruktionerna i steg 1, och kör kommandot för ditt system:

**Windows PowerShell:**

```powershell
agents-opencode install --lang sv
```

Om Windows inte hittar kommandot, använd launchern direkt:

```powershell
& "$env:LOCALAPPDATA\agents-opencode\bin\agents-opencode.cmd" install --lang sv
```

**Linux Terminal** — använd den fullständiga sökvägen; ingen PATH-ändring behövs:

```bash
"$HOME/.local/bin/agents-opencode" install --lang sv
```

Om guiden erbjuder att göra mappen till ett Git-projekt kan du tacka ja till `git init` eller tacka nej. För att tacka ja måste Git vara installerat. I ett projekt med filer, tacka bara ja om du vill att Git ska börja hantera projektet.

## Steg 5 — gör val i guiden

Ta god tid på dig och läs frågorna. Om du vill avbryta utan att spara agentkonfigurationen, svara nej på frågan om att spara. En eventuell mapp eller Git-historik som du redan valt att skapa tas inte bort när du avbryter.

1. **Agenter:** välj `c` för det föreslagna kärnteamet. Det räcker för en första genomgång; du behöver inte välja alla specialister.
2. **Modeller:** välj ett nummer från listan som hämtas med `opencode models`. Att modellen syns betyder inte att kontot är inloggat eller att anropet fungerar. Kontrollera provider och pris separat. Inga modell-ID:n eller API-nycklar följer med paketet.
3. **Informationsklassning:** välj efter vilken projektinformation den valda modellen får se. `PRIVATE` ska bara väljas för verifierat lokalt hostade modeller. Molnmodeller kan få se projektets instruktioner och innehåll. `HYBRID` blandar lokal och molnanvändning; det skyddar inte automatiskt känslig information.
4. **Behörighetsprofil:** välj **1 — Låst arbetsdator** för ett försiktigt första försök; standardvalet är annars **2**. Läs varje följdfråga: `ask` betyder fråga först, `deny` neka och `allow` tillåta utan fråga. Låt obevakat läge vara avstängt. Bekräfta behörighetsprofilen med ja när den stämmer, annars avbryts guiden.
5. Läs sammanfattningen. När guiden frågar om den ska spara projektkonfiguration och profiler, svara **ja** bara om valen stämmer. Standardvalet på frågan om att spara är **nej**; tryck Enter för nej.

`SHAREABLE` är klassningen för information som får delas med godkända molnmodeller. Prova bara med material utan hemligheter eller personuppgifter om du är osäker. `PRIVATE` kräver att du har verifierat att modellanslutningarna verkligen är lokala, inte bara att modellen har ett visst namn.

## Steg 6 — starta och ge en första uppgift

Kör startkommandot **från projektmappen**.

**Windows PowerShell:**

```powershell
agents-opencode run
```

Om kommandot inte hittas, använd:

```powershell
& "$env:LOCALAPPDATA\agents-opencode\bin\agents-opencode.cmd" run
```

**Linux Terminal:**

```bash
"$HOME/.local/bin/agents-opencode" run
```

När OpenCode öppnas skriver du uppgiften där. Börja gärna med denna försiktiga fråga:

> Läs projektets instruktioner. Beskriv kort vad projektet gör och vilka viktiga filer och tester du hittar. Ändra inga filer, installera inga paket och använd inte nätverket. Föreslå ett litet nästa steg och invänta mitt godkännande.

Om du valde kärnteamet är orkestreraren redan huvudagent; inget extra aktiveringskommando behövs. Lägg senare till programmerare och testare med `agents-opencode agents` på Windows eller `"$HOME/.local/bin/agents-opencode" agents` på Linux om du vill att teamet också ska skriva kod. Starta om OpenCode efter ändringar i konfigurationen. Agenternas instruktioner är på engelska, men du kan be om svar på svenska.

Kommandona `resume` och `status` körs också från projektmappen:

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

## Fördjupning och felsökning

- **Modellkontot/priset:** modelllistan är ingen inloggnings- eller betalningskontroll. Om anrop misslyckas, kontrollera OpenCode-providerinställningar, konto och leverantörens priser.
- **Windows hittar inte `agents-opencode`:** öppna ett nytt terminalfönster. Om det fortfarande inte fungerar, använd den fullständiga launchersökvägen ovan. OpenCode på Windows kan ha separata krav såsom Git Bash.
- **Linux hittar inte kommandot:** den här guiden använder avsiktligt `"$HOME/.local/bin/agents-opencode"`. Installationsprogrammet lägger inte till `~/.local/bin` i PATH.
- **Git:** Git är separat. Projektguiden erbjuder att initiera Git om det saknas; du får tacka nej.
- **JSONC:** installationsverktyget hanterar `opencode.json`, inte kommenterad `opencode.jsonc`. Läs och slå ihop befintlig konfiguration varsamt.
- **Windows-verifiering:** native Windows-installation och end-to-end-användning har inte verifierats här. Linux-kontroller har körts; vissa Windows-tester hoppas över på Linux.
- **Säkerhet:** behörighetsregler i OpenCode är inte en OS-sandbox eller brandvägg. För mer om `ask`, `deny`, `allow`, molndata och obevakat läge, se säkerhetsavsnitten i [README.md](README.md).
