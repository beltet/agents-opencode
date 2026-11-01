# Säkerhetsgränser

OpenCode 1.x har ett dokumenterat verktygsbehörighetssystem (allow / ask / deny). Den här applikationen skriver rollspecifika verktygsregler till `opencode.json`. Den är **inte** en brandvägg, drivrutinsisolering eller en OS-sandbox.

## Kan i viss utsträckning styras tekniskt

- Agentens rätt att läsa, skriva och köra shellverktyget via OpenCode V1-konfiguration.
- Agentens rätt att anropa andra agenter via `task`.
- Vissa mönsterbaserade Git- och firmwarekommandoavslag i Bash.
- Extern katalogåtkomst via OpenCodes `external_directory`.

## Rådgivande i denna beta

- URL/domänallowlist och blocklist för kommandon och externa processer.
- USB-enhets-ID och fysisk hårdvaruåtkomst.
- Exakta nätverksdiskar, remotes, branscher och begränsning till enskilda Git-servrar.
- Exakta filsystemallowlist/denylist för godtycklig shellkod.
- Firmwareflashning via alternativa verktyg eller direkta systemanrop.

## Rekommenderade skydd

Kör med separat oprivilegierad OS-användare och filrättigheter, isolera riskfylld projektkod i VM/container, använd brandvägg där strikt nätverkspolicy behövs, och låt SSH-servern kontrollera Git-åtkomst. Ge inte projektteamet full shellaccess mot hemliga konton, firmwarenheter eller produktionssystem.

En modell kan alltid ha fel. Obevakad körning kräver särskild försiktighet: `ask` kan då godkännas automatiskt av OpenCode beroende på körläge. Verkligt förbjudna operationer ska vara `deny` och dessutom tekniskt avskärmade där möjligt.

Projektbackuper kan innehålla privata konfigurationsuppgifter. Publicera dem inte i offentliga Git-repositoryn.
