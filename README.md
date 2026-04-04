# CodeRoblox

CodeRoblox ist das Start-Repository fuer eine Codex-gestuetzte Roblox-Entwicklungsumgebung.

## Ziel
- Codex mit Roblox Studio ueber ein Studio-Plugin und einen lokalen Agent verbinden
- Roblox-Spiele mit nachvollziehbaren, pruefbaren Aenderungen entwickeln
- klassische Software-Engineering-Praktiken wie Git, Tests, Makefiles und CI nutzen

## Aktueller Stand
- initiales Anforderungsdokument: `implementation_plan.md`
- lokaler Python-Agent fuer Sessions, Snapshots, Checkpoints und Operations-Queues
- Roblox-Studio-Plugin-Grundgeruest mit Snapshot-Push und Batch-Polling
- Testfaelle fuer Agent-Logik und Luau-Hilfsmodule
- GitHub Actions CI fuer Lint, Tests und Plugin-Build

## Repository-Struktur
- `src/coderoblox_agent`: lokaler Agent und HTTP-API
- `plugin/src`: Roblox-Studio-Plugin
- `plugin/tests`: Luau-Spezifikationstests, ausgefuehrt mit `lune`
- `skills/coderoblox`: installierbarer Codex-Skill fuer dieses Repository
- `CLAUDE.md`: Projektanweisungen fuer Claude
- `.github/workflows/ci.yml`: Continuous Integration
- `implementation_plan.md`: zugrunde liegendes Anforderungsdokument

## Voraussetzungen
- `python3`
- `make`
- `mise`
- Roblox-CLI-Tools ueber `mise`: `rojo`, `lune`, `stylua`, `selene`

## Installation

### 1. Repository vorbereiten
Projekt-Tooling aktivieren und den lokalen `mise.toml` einmal als vertrauenswuerdig markieren:

```bash
mise trust .
```

Danach den aktuellen Zustand pruefen:

```bash
make ci
```

### 2. Lokalen Agent starten
Der Plugin-Bridge-Server laeuft lokal auf Port `8787`:

```bash
python3 scripts/run_agent.py --host 127.0.0.1 --port 8787
```

Unter WSL2 ist `127.0.0.1` in der Regel direkt von Roblox Studio unter Windows erreichbar.

### 3. Plugin bauen
Das Roblox-Plugin wird als lokale `.rbxm`-Datei erzeugt:

```bash
make build-plugin
```

Danach liegt das Artefakt hier:

```text
build/CodeRobloxPlugin.rbxm
```

### 4. Plugin in Roblox Studio installieren
Empfohlener Weg:
1. Roblox Studio starten.
2. Einen beliebigen Place oeffnen.
3. Den lokalen Plugin-Ordner in Studio oeffnen.
4. Die Datei `build/CodeRobloxPlugin.rbxm` in den lokalen Plugin-Ordner kopieren.
5. Roblox Studio neu starten.

Alternative:
1. `build/CodeRobloxPlugin.rbxm` in Studio importieren.
2. Das importierte Plugin-Modell als lokalen Plugin-Eintrag speichern.

### 5. Plugin in Roblox Studio konfigurieren
Nach dem Neustart:
1. In Studio das Plugin `CodeRoblox` oeffnen.
2. Als Agent-URL `http://127.0.0.1:8787` eintragen.
3. `Connect Session` klicken.
4. Optional `Push Snapshot` klicken, um den ersten Studio-Kontext an den Agenten zu senden.

### 6. HTTP-Zugriff erlauben
Das Plugin spricht ueber `HttpService` mit dem lokalen Agenten. Je nach Studio-Kontext musst du HTTP-Zugriff fuer das Projekt bzw. Plugin erlauben. Wenn Roblox Studio beim ersten Request nach einer Berechtigung fragt, diese bestaetigen.

## Codex- und Claude-Skill installieren

### Codex-Skill
Im Repository liegt ein installierbarer Skill unter:

```text
skills/coderoblox
```

Installiere ihn, indem du den Ordner in dein Codex-Skill-Verzeichnis kopierst oder symlinkst:

```text
$CODEX_HOME/skills/coderoblox
```

Falls `CODEX_HOME` nicht gesetzt ist, ist der uebliche Standard:

```text
~/.codex/skills/coderoblox
```

Der Skill enthaelt:
- repo-spezifische Arbeitsregeln
- wichtige Dateien und Befehle
- den Agent-Plugin-Workflow
- Verifikationsschritte wie `make ci`

### Claude
Fuer Claude liegt die Projektanweisung in:

```text
CLAUDE.md
```

Wenn Claude mit dem Repository arbeitet, sollte diese Datei als projektlokale Arbeitsanweisung geladen werden.

## Wie Plugin und Skill zusammenhaengen
Wichtig ist die Trennung:
- Das Roblox-Studio-Plugin ist die Laufzeitbruecke zu Roblox Studio.
- Der lokale Agent ist die Laufzeitbruecke zwischen Studio und dem Repository.
- Der Codex-Skill bzw. `CLAUDE.md` ist die Arbeitsanweisung fuer die AI.

Das bedeutet:
1. Das Plugin verbindet Roblox Studio mit dem lokalen Agenten.
2. Der Skill erklaert Codex, wie dieses Repo aufgebaut ist und welche Befehle und Regeln gelten.
3. Zusammen kann die AI zielgerichteter mit dem Plugin-Agent-Stack arbeiten.

Praktisch verwendest du beides gemeinsam so:
1. Codex-Skill installieren oder Claude mit `CLAUDE.md` arbeiten lassen.
2. Lokalen Agent mit `python3 scripts/run_agent.py --host 127.0.0.1 --port 8787` starten.
3. Plugin mit `make build-plugin` bauen und in Roblox Studio installieren.
4. Plugin in Studio mit `http://127.0.0.1:8787` verbinden.
5. Danach kann die AI repo-spezifisch arbeiten und die Studio-Verbindung gezielt nutzen.

## Lokale Entwicklung
Checks ausfuehren:

```bash
make lint
make test
make build-plugin
make ci
```

## Implementierter Workflow
1. Das Studio-Plugin verbindet sich mit dem lokalen Agenten und startet eine Session.
2. Das Plugin uebertraegt Snapshot-Daten aus Roblox Studio.
3. Der Agent validiert und queue-t aendernde Operationen mit Checkpoints.
4. Das Plugin pollt neue Batches, wendet unterstuetzte Operationen an und meldet Resultate zurueck.

## Bekannte Grenzen des aktuellen Stands
- `rollback_checkpoint` ist im Plugin noch als explizites TODO markiert.
- `apply_script_patch` nutzt aktuell direkt `Source`; spaeter sollte das auf `ScriptEditorService` verfeinert werden.
- Playtest- und Diagnostics-Roundtrips sind im Protokoll angelegt, aber noch nicht voll implementiert.
