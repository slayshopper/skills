# SlayShopper Skills

Umiejętności (skills) agentów do integracji z [SlayShopper](https://slay.cytr.us) — wyszukiwarką produktów przez MCP. Każdy skill zamienia wynik `shopping_assistant` w listing produktów ze zdjęciami, z deduplikacją, sortowaniem po cenie i regułami „nie zmyślaj".

## Zawartość

- [`skills/slayshopper-shopping/`](skills/slayshopper-shopping/) — wyszukiwanie produktów, porównywanie cen i listing ze zdjęciami.

## Instalacja

### 1. Serwer MCP (wymagane)

Skill zakłada, że narzędzie `shopping_assistant` serwera MCP `slayshopper` jest podłączone. Klucz API generujesz na https://slay.cytr.us/settings.

- **Hermes Agent**
  ```bash
  hermes mcp add slayshopper --url https://slay.cytr.us/mcp --auth header
  ```
- **Claude Code**
  ```bash
  claude mcp add --transport http slayshopper https://slay.cytr.us/mcp --header "Authorization: Bearer $KEY"
  ```
- **OpenCode / Claude Desktop / Cursor** — patrz https://slay.cytr.us/mcp-model-context-protocol

### 2. Skill

- **skills.sh** (każdy agent): `npx skills add slayshopper/skills --skill slayshopper-shopping`
- **ClawHub / OpenClaw**: `openclaw skills install @slayshopper/slayshopper-shopping`
- **Hermes**: `hermes skills install well-known:https://slay.cytr.us/.well-known/skills/slayshopper-shopping`

## Licencja

MIT — patrz [LICENSE](LICENSE).
