# Börja här – Agents OpenCode GUI

En vanlig grafisk applikation för att välja vilka OpenCode-agenter som ska
installeras i **ett visst projekt**, med exakt vilka modeller och behörigheter.
Programmet analyserar inte projektet och byter aldrig modell automatiskt.

## Hämta programmet

Gå till GitHub: <https://github.com/beltet/agents-opencode/releases>

När GUI-koden har publicerats och dess GitHub Actions-bygge lyckats:

- **Windows:** ladda ner `agents-opencode-windows-x64.zip`, packa upp **hela**
  mappen och dubbelklicka på `agents-opencode.exe`.
- **Linux:** ladda ner `agents-opencode-linux-x64.AppImage`, högerklicka och
  tillåt körning, och öppna filen. Vissa distroer kräver FUSE/libfuse2.
- **macOS:** välj DMG-filen för Intel eller Apple Silicon, öppna den och flytta
  appen till Program/Applications. Osignerade appar kan kräva manuell
  säkerhetsbekräftelse.

**Finns inga releasefiler än?** Källkoden måste först pushas till GitHub,
byggas på Actions och publiceras från en versionstagg. Se `docs/ERSATT_GITHUB.md`.

## Konfigurera agentteamet

1. Starta programmet och välj din projektmapp med **Välj mapp…**.
2. Skriv kort vad du vill bygga på fliken **Projekt**.
3. Markera agentroller och ange ett modell-ID (`provider/model`) per agent.
   `orchestrator` är alltid med. Ingen modell väljs automatiskt.
4. Välj åtkomstnivåer under **Behörigheter**; lämna firmware och USB på
   **Neka** om det inte behövs.
5. Om du använder Git, ange lokalt repository eller remote och Git-identitet
   på fliken **Git / SSH**.
6. Klicka **Visa ändringar** och läs förhandsgranskningen.
7. Klicka **Spara och installera agentteam**. Backup tas av hanterade filer.
8. Starta OpenCode som vanligt **i projektmappen**.

Observera att URL-listor, USB- och firmwaretillstånd är **rådgivande regler**,
inte en säker operativsystemssandbox. OpenCode och AI-modeller installeras
separat.

## Bygg själv

På Fedora: `sudo dnf install cmake ninja-build gcc-c++ qt6-qtbase-devel git`.
Sedan från källkodsmappen:

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel "$(nproc)"
ctest --test-dir build --output-on-failure
./build/agents-opencode
```

Mer information finns i `README.md` och `docs/ERSATT_GITHUB.md`.
