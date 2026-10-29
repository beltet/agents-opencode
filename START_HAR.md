# Börja här – OpenCode Agentteam 2.0

Installera genom att packa upp ZIP-filen och köra `bash install.sh` i den uppackade katalogen. Det ersätter den gamla centrala versionen av `agents-opencode` utan att ta bort befintliga projekt.

Starta i ett Git-projekt: `cd ~/git/ditt-projekt && agents-opencode`.

Välj **1** för hela guiden: urval av agenter, hela listan från `opencode models` för varje vald agent, informationsklassning och egna behörighetsval.

Senare kan du välja **2** för att byta alla agentmodeller, **3** för att lägga till eller ta bort agenter, **4** för att ändra rättigheter, **6** för att skapa en ny agent, **7** för att starta OpenCode och **8** för att återuppta en session.

Läs `README.md` om särskilt säkerhetsfrågorna: OpenCodes behörigheter ger inte pålitligt nätverks-/filsystemskydd för shellkommandon. Använd en isolerad VM när agentteamet ska ha mycket stor frihet.

## Nytt i v2.1: vit- och svartlistor

Kör `agents-opencode access` inne i projektet. Där kan du välja tillåtna och blockerade **lokala kataloger, nätverksdiskar och internetvärdar**. Normalt är all åtkomst utanför projektmappen blockerad om du inte uttryckligen väljer breda VM-rättigheter. Reglerna sparas i `AGENT_ACCESS_POLICY.json`, och engelska instruktioner laddas av OpenCode.

Vill du ändra filen manuellt, kör sedan `agents-opencode sync-access` och starta om OpenCode. Ett enkelt kontrollkommando är `python3 .opencode/tools/access_check.py path read /mnt/disk/fil.txt`.

**VARNING: Det är inte riktig säkerhet.** Ett tillåtet shellkommando kan komma åt andra sökvägar eller kontakta andra adresser oavsett vad reglerna säger. Säker begränsning kräver OS-/VM-/containeråtkomstkontroll och nätverksfilter. OpenCode 1.x kan inte nativt begränsa `webfetch` per domän.
