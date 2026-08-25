# Palopedix Agent Guidelines

All AI coding agents (Antigravity) operating within this repository MUST follow these workspace rules:

1. **Mandatory First Read**: Read [PALOPEDIX_AGENT_GUIDE.md](file:///c:/AI/palopedix/PALOPEDIX_AGENT_GUIDE.md) before formulating any plan, generating answers, or executing any task in this codebase.
2. **No Ad-Hoc Scripts / Parsers**: Never write temporary `.py` scrapers, exploratory parser scripts, or ad-hoc DB dumpers. Always utilize the built-in CLI commands (`python -m palengine.cli.main ... --format json`), REST API endpoints, or `SQLiteEngine` methods.
3. **No Unrequested Logic Alterations**: Keep changes surgical and strictly aligned with the user prompt. Do not modify parsing hints, generator scoring weights, or core calculations unless explicitly instructed.
4. **Clean Workspace**: Do not leave temporary scripts, json dumps, or scratch logs in the workspace root.
