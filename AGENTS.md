# Palopedix Agent Guidelines

All AI coding agents (Antigravity) operating within this repository MUST follow these workspace rules:

1. **Mandatory First Read**: Read [PALOPEDIX_AGENT_GUIDE.md](file:///c:/AI/palopedix/PALOPEDIX_AGENT_GUIDE.md) before formulating any plan, generating answers, or executing any task in this codebase.
2. **Use Existing Tools & Data Exclusively**: Never write new speculative code, ad-hoc fallback catalogs, hardcoded logic branches, or workaround parser scripts. Always solve tasks using exclusively existing tools, existing database schemas/tables (`pals`, `partner_skills`, `partner_skill_categories`, `pal_partner_skill_categories`, etc.), REST endpoints, CLI commands, and `SQLiteEngine` methods.
3. **Missing Functionality / Data Protocol**: If a task requires functionality, data, or tables that do not exist or are incomplete in current tools/databases, the agent MUST NOT attempt in-code workarounds or ad-hoc patches. Instead, the agent MUST STOP, describe the missing components or data to the user, and ask for explicit instruction/approval before adding any new code.
4. **No Unrequested Logic Alterations**: Keep changes surgical and strictly aligned with the user prompt. Do not modify parsing hints, generator scoring weights, or core calculations unless explicitly instructed.
5. **Binary Stream & Serialization Integrity**:
   - When extending or patching save binary readers/parsers (`GvasFile`, `FArchiveReader`), NEVER skip raw bytes using unverified offsets.
   - All property headers (`set_type`, `key_type`, `value_type`, `struct_id`, `_id`) MUST be fully unpacked before attempting payload seeks to guarantee 100% stream alignment.
6. **Database Concurrency & DDL Hygiene**:
   - Connection initialization (`__init__` or `_create_tables`) MUST NEVER execute destructive DDL (`DROP TABLE`) on existing application tables.
   - All schema creations must be strictly idempotent (`CREATE TABLE IF NOT EXISTS`).
   - External database attachments (`ATTACH DATABASE`) must be guarded against duplicate attachment exceptions to prevent SQLite locks during concurrent FastAPI requests.
7. **Data Contract Rigor**:
   - Never assume nested data types (e.g. assuming `passives` is `list[str]` when `query_instances` produces `list[dict]`).
   - Verify the exact shape of database rows and analytics outputs across callers before invoking string/list methods.
8. **Clean Workspace**: Do not leave temporary scripts, json dumps, or scratch logs in the workspace root.


