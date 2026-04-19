# CodeRoblox

CodeRoblox ist das Start-Repository fuer eine Codex-gestuetzte Roblox-Entwicklungsumgebung.

## Ziel
- Codex mit Roblox Studio ueber ein Studio-Plugin und einen lokalen Agent verbinden
- Roblox-Spiele mit nachvollziehbaren, pruefbaren Aenderungen entwickeln
- klassische Software-Engineering-Praktiken wie Git, Tests, Makefiles und CI nutzen

## Aktueller Stand
- initiales Anforderungsdokument: `implementation_plan.md`
- lokaler Python-Agent fuer Sessions, Snapshots, Script-Dokumente, lokalen Mirror, Checkpoints, Approval-Gates und Operations-Queues
- Roblox-Studio-Plugin mit Kontext-Sync, lokalem Output-Kontext, Rollback-Unterstuetzung und agentischem `auto_apply_safe`-Standardmodus
- Testfaelle fuer Agent-Logik und Luau-Hilfsmodule
- GitHub Actions CI fuer Lint, Tests und Plugin-Build

## Repository-Struktur
- `src/coderoblox_agent`: lokale Agent-Runtime und HTTP-Endpunkt fuer das Plugin
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
Arbeite im Repo und setze die lokalen Variablen passend zu deiner Shell.

Empfohlene lokale Pfade fuer diese Maschine:
- Repository: `C:\Users\tom\Documents\GitHub\Code4Roblox`
- Roblox-Plugin-Ordner: `C:\Users\tom\AppData\Local\Roblox\Plugins`
- Codex-Home: `C:\Users\tom\.codex`

Unter WSL entsprechen diese Pfade:
- Repository: `/mnt/c/Users/tom/Documents/GitHub/Code4Roblox`
- Roblox-Plugin-Ordner: `/mnt/c/Users/tom/AppData/Local/Roblox/Plugins`
- Codex-Home: `/mnt/c/Users/tom/.codex`

### 1a. Lokale Pfade als Umgebungsvariablen setzen
Die lokalen Maschinenpfade sollten nicht im Repo gespeichert werden, sondern in deiner Shell-Umgebung liegen.

Fuer WSL in `~/.bashrc`:

```bash
export CODEX_HOME=/mnt/c/Users/tom/.codex
export ROBLOX_PLUGIN_DIR=/mnt/c/Users/tom/AppData/Local/Roblox/Plugins
```

Danach die Shell neu laden:

```bash
source ~/.bashrc
```

Pruefen:

```bash
echo "$CODEX_HOME"
echo "$ROBLOX_PLUGIN_DIR"
```

Fuer PowerShell zum Beispiel im Profil oder pro Sitzung:

```powershell
$env:CODEX_HOME = 'C:\Users\tom\.codex'
$env:ROBLOX_PLUGIN_DIR = 'C:\Users\tom\AppData\Local\Roblox\Plugins'
```

Pruefen:

```powershell
$env:CODEX_HOME
$env:ROBLOX_PLUGIN_DIR
```

Bash / WSL:

```bash
cd /pfad/zu/CodeRoblox
source scripts/use-local-env.sh
```

PowerShell unter Windows:

```powershell
Set-Location C:\Users\tom\Documents\GitHub\Code4Roblox
. .\scripts\use-local-env.ps1
```

Falls PowerShell lokale Skripte blockiert, reicht fuer die aktuelle Sitzung:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
. .\scripts\use-local-env.ps1
```

Das Skript setzt:
- `CODEROBLOX_ROOT` auf das aktuelle Repository
- `CODEX_HOME` auf `${HOME}/.codex`, falls es nicht schon gesetzt ist
- `CODEROBLOX_PLUGIN_FILE` auf das gebaute Plugin-Artefakt

Wichtig:
- `use-local-env` setzt `CODEX_HOME` nur dann selbst, wenn die Variable noch nicht gesetzt ist.
- Wenn du `CODEX_HOME` schon bewusst auf `/mnt/c/Users/tom/.codex` oder `C:\Users\tom\.codex` gesetzt hast, bleibt dieser Wert erhalten.
- `ROBLOX_PLUGIN_DIR` muss aus deiner Shell-Umgebung kommen und wird nicht vom Repo vorgegeben.

Fuer WSL zum Beispiel:

```bash
export CODEX_HOME=/mnt/c/Users/tom/.codex
export ROBLOX_PLUGIN_DIR=/mnt/c/Users/tom/AppData/Local/Roblox/Plugins
```

Projekt-Tooling aktivieren und den lokalen `mise.toml` einmal als vertrauenswuerdig markieren:

```bash
mise trust .
```

Danach den aktuellen Zustand pruefen:

```bash
make ci
```

Wenn `CODEX_HOME` bereits gesetzt ist, kannst du den lokalen Codex-Skill auch direkt ueber `make` installieren:

```bash
make install-skill
```

Das installiert ein echtes Skill-Verzeichnis nach:

```text
$CODEX_HOME/skills/coderoblox
```

Falls `CODEX_HOME` oder `$CODEX_HOME/skills` noch nicht existieren, legt `make install-skill` diese Ordner automatisch an.

### 2. Lokalen Agent starten
Der lokale Agent stellt auf Port `8787` den Endpunkt bereit, mit dem sich das Roblox-Studio-Plugin verbindet.

Bash / WSL:

```bash
source scripts/use-local-env.sh
cd "$CODEROBLOX_ROOT"
python3 scripts/run_agent.py --host 127.0.0.1 --port 8787
```

PowerShell:

```powershell
. .\scripts\use-local-env.ps1
Set-Location $env:CODEROBLOX_ROOT
python .\scripts\run_agent.py --host 127.0.0.1 --port 8787
```

### 3. Plugin bauen
Das Roblox-Plugin wird als lokale `.rbxm`-Datei erzeugt:

```bash
source scripts/use-local-env.sh
cd "$CODEROBLOX_ROOT"
make build-plugin
```

Danach liegt das Artefakt hier:

```bash
echo "$CODEROBLOX_PLUGIN_FILE"
```

In PowerShell entspricht das lokal diesem Pfad:

```powershell
$env:CODEROBLOX_ROOT\build\CodeRobloxPlugin.rbxm
```

Wenn `ROBLOX_PLUGIN_DIR` gesetzt ist, kopiert `make build-plugin` das Plugin automatisch in diesen lokalen Roblox-Plugin-Ordner.

Auf dieser Maschine ist das typischerweise:

```text
C:\Users\tom\AppData\Local\Roblox\Plugins
```

### 4. Plugin in Roblox Studio installieren
Mit gesetztem `ROBLOX_PLUGIN_DIR` passiert das beim Build automatisch.

Ohne gesetzte Umgebungsvariable:
1. Roblox Studio starten.
2. Einen beliebigen Place oeffnen.
3. Den lokalen Plugin-Ordner in Studio oeffnen.
4. Die Datei aus `"$CODEROBLOX_PLUGIN_FILE"` in den lokalen Plugin-Ordner kopieren.
5. Roblox Studio neu starten.

Alternative:
1. Die Datei `"$CODEROBLOX_PLUGIN_FILE"` in Studio importieren.
2. Das importierte Plugin-Modell als lokalen Plugin-Eintrag speichern.

### 5. Plugin in Roblox Studio konfigurieren
Nach dem Neustart:
1. In Studio das Plugin `CodeRoblox` oeffnen.
2. In das Feld `Agent URL` `http://127.0.0.1:8787` eintragen.
3. `Connect Session` klicken.
4. `Sync Studio Context` klicken, um den ersten Studio-Kontext an den Agenten zu senden.

### 6. HTTP-Zugriff erlauben
Das Plugin spricht ueber `HttpService` mit dem lokalen Agenten. Je nach Studio-Kontext musst du HTTP-Zugriff fuer das Projekt bzw. Plugin erlauben. Wenn Roblox Studio beim ersten Request nach einer Berechtigung fragt, diese bestaetigen.

## Codex- und Claude-Skill installieren

### Codex-Skill
Im Repository liegt ein installierbarer Skill unter `skills/coderoblox`.

Installieren:

Bash / WSL:

```bash
source scripts/use-local-env.sh
make install-skill
```

PowerShell:

```powershell
. .\scripts\use-local-env.ps1
. .\scripts\install-codex-skill.ps1
```

Das Skript verlinkt den Skill nach:

```bash
echo "$CODEX_HOME/skills/coderoblox"
```

Der komplette Skill-Ordner inklusive Referenzen und Hilfsdateien wird dabei in das lokale Codex-Home kopiert.

Auf dieser Maschine ist das typischerweise:

```text
C:\Users\tom\.codex\skills\coderoblox
```

Der Skill enthaelt:
- repo-spezifische Arbeitsregeln
- wichtige Dateien und Befehle
- den Agent-Plugin-Workflow
- Verifikationsschritte wie `make ci`

### Claude
Fuer Claude liegt die Projektanweisung in `CLAUDE.md`.

Wenn Claude mit dem Repository arbeitet, sollte diese Datei als projektlokale Arbeitsanweisung geladen werden.

## Wie Plugin und Skill zusammenhaengen
Wichtig ist die Trennung:
- Das Roblox-Studio-Plugin ist die Studio-seitige Laufzeit fuer Lesen, Schreiben und Status in Roblox Studio.
- Der lokale Agent ist die Laufzeit im Repository und stellt den lokalen Endpunkt fuer das Plugin bereit.
- Der Codex-Skill bzw. `CLAUDE.md` ist die Arbeitsanweisung fuer die AI.

Das bedeutet:
1. Das Plugin verbindet Roblox Studio mit dem lokalen Agenten.
2. Der lokale Agent stellt der externen KI Snapshots, Script-Dokumente, Audit-Infos, lokalen Mirror, Validierung und Queueing bereit.
3. Der Skill erklaert Codex oder Claude, wie mit diesem Kontext geplant und wie sicher in Studio angewendet wird.
4. Zusammen kann die AI zielgerichteter mit der Agent-Runtime und dem Plugin arbeiten.

Praktisch verwendest du beides gemeinsam so:
1. Codex-Skill installieren oder Claude mit `CLAUDE.md` arbeiten lassen.
2. `source scripts/use-local-env.sh` ausfuehren.
3. Den lokalen Agent mit `python3 scripts/run_agent.py --host 127.0.0.1 --port 8787` starten.
4. Das Plugin mit `make build-plugin` bauen und in Roblox Studio installieren.
5. Plugin in Studio mit `http://127.0.0.1:8787` verbinden.
6. Danach kann die AI repo-spezifisch arbeiten und die Studio-Verbindung gezielt nutzen.

## Lokale Entwicklung
Checks ausfuehren:

Bash / WSL:

```bash
source scripts/use-local-env.sh
cd "$CODEROBLOX_ROOT"
make lint
make test
make build-plugin
make install-skill
make ci
```

PowerShell:

```powershell
. .\scripts\use-local-env.ps1
Set-Location $env:CODEROBLOX_ROOT
make lint
make test
make build-plugin
make ci
```

## Implementierter Workflow
1. Das Studio-Plugin verbindet sich mit dem lokalen Agenten und startet eine Session.
2. Das Plugin synchronisiert Studio-Kontext als Snapshot plus Script-Dokumente.
3. Der Agent schreibt daraus einen lokalen Mirror unter `studio_mirror/<projektname>/`, inklusive `snapshot.json`, `mirror_manifest.json` und versionierbaren Luau-Dateien.
4. Die externe KI liest diesen Kontext ueber den lokalen Agenten und kann zusaetzlich den lokalen Mirror fuer Git, Diff und Dateibearbeitung nutzen.
5. Die externe KI plant strukturierte Operationen.
6. Der Agent validiert Operationen. Im Standardmodus `auto_apply_safe` werden nicht-destruktive Aenderungen ohne Klick angewendet, riskante oder destruktive Batches landen weiter in `pending_approval`.
7. Das Plugin wendet freigegebene oder automatisch zugelassene Batches an, meldet Resultate zurueck und synchronisiert den aktuellen Studio-Zustand erneut.

## Lokaler Mirror
Nach jedem Snapshot-Sync schreibt der Agent einen git-freundlichen Spiegel des Studio-Zustands nach:

```text
studio_mirror/<projektname>/
  mirror_manifest.json
  snapshot.json
  scripts/
```

Die Skripte werden dabei nach Roblox-Pfaden abgelegt, zum Beispiel:

```text
studio_mirror/MyPlace/scripts/ReplicatedStorage/MyModule.module.luau
```

Der Mirror ist dafuer gedacht, von Codex oder Claude gelesen, gedifft und optional in Git versioniert zu werden.

## Bekannte Grenzen des aktuellen Stands
- `rollback_checkpoint` funktioniert aktuell nur fuer Checkpoints, die in derselben Plugin-Session angelegt und angewendet wurden.
- `apply_script_patch` nutzt bevorzugt `ScriptEditorService`, faellt bei Bedarf aber noch auf direktes `Source`-Schreiben zurueck.
- Output- und einfache Diagnostics-Roundtrips sind verfuegbar; vollwertige Playtest-Automation bleibt weiterhin von Studio-Kontext und Roblox-APIs abhaengig.
