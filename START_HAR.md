# Börja här – OpenCode Agentteam

## Windows (native)

Krav: Windows, Python 3.10 eller senare, Git och OpenCode installerat/konfigurerat separat. Installationsprogrammet kräver inte Bash, administratörsrättigheter eller Python-paket. OpenCode har egna plattformskrav och kan på Windows behöva Git Bash; kontrollera OpenCodes dokumentation. Det kravet gäller inte `install.cmd`.

1. Hämta hela källarkivet från GitHub med **Code → Download ZIP**. Det finns ingen separat release-binär. Packa upp hela arkivet.
2. I CMD: gå till den uppackade katalogen och kör `install.cmd`. Ange språk direkt med `install.cmd --lang sv` eller `install.cmd --lang en`. I PowerShell: gå till katalogen med `Set-Location` och kör `.\install.cmd` eller `.\install.cmd --lang sv` / `.\install.cmd --lang en`. Språk väljs först; Enter väljer engelska.
   Lägg till `--no-path` i installationskommandot (t.ex. `install.cmd --no-path`) för att avstå från automatisk PATH-registrering.
3. I CMD, starta `agents-opencode.cmd` från den uppackade katalogen eller kör den installerade filen:

   ```text
   "%LOCALAPPDATA%\agents-opencode\bin\agents-opencode.cmd"
   ```

   I PowerShell, kör `& "$env:LOCALAPPDATA\agents-opencode\bin\agents-opencode.cmd"`. Som standard registreras katalogen i den aktuella användarens PATH via HKCU; befintliga poster bevaras, dubbletter undviks och administratörsrättigheter behövs inte. Lägg till `--no-path` vid installationen för att avstå. Vid fel visas ett åtgärdsinriktat meddelande, men startprogrammet finns kvar och kan köras med full sökväg. Ändringen gäller nya processer, inte öppna terminaler. Öppna en ny terminal; om Windows Terminal eller en IDE fortfarande har gammal miljö, starta om hela värdprogrammet eller logga ut och in igen. Python-underprocesser kan inte ändra förälderns terminalmiljö.
4. Gå till ett Git-projekt och starta managern. Välj **1** för hela konfigurationsguiden. CMD-exempel: `agents-opencode.cmd install --lang sv`. PowerShell-exempel: `.\agents-opencode.cmd install --lang sv`. Interaktiv körning frågar om språk först; Enter väljer engelska. I icke-interaktiv körning är standardspråket engelska.

## Linux

Packa upp hela arkivet och kör `bash install.sh`. Starta därefter `agents-opencode` från ett projekt. Bash behövs för Linux-installationen; ingen root-behörighet eller Python-paket krävs.

## Guiden och delning

Guiden låter dig välja agenter, modeller från den separat installerade OpenCode-kommandot `opencode models`, informationsklassning och behörigheter. Modeller eller API-nycklar förväljs inte. Agentprofiler och genererade projektinstruktioner är på engelska även när managergränssnittet är svenskt.

Dela hela det kuraterade källarkivet, till exempel GitHubs **Code → Download ZIP**. Dela inte en lokal managerinstallation eller en konfigurerad projektrepository som om de vore installationspaketet. Projektets `opencode.json`, `AGENTS.md`, `PROJECT_POLICY.md`, `AGENT_ACCESS_POLICY.json` och `.opencode/` är lokal, genererad konfiguration. `AGENT_CAST.md` är en fiktiv och frivillig presentation av rollerna; den beskriver inte riktiga personer och ändrar inte agenternas roller eller mandat.

**Säkerhet:** OpenCodes behörigheter och åtkomstpolicy är inte en sandbox eller brandvägg. Tillåtna shellkommandon och program kan använda värdkontots åtkomst. För verklig begränsning krävs OS-/VM-/containerkontroller och nätverksfilter. Läs säkerhetsavsnitten i `README.md` innan du väljer breda rättigheter eller obevakad körning.

Windows-installationen är implementerad, men har inte verifierats genom native Windows-test här. Linux-kontroller har körts; vissa Windows-specifika tester hoppas över på Linux.
