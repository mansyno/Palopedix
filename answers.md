Here are the answers and design decisions for all 8 points to clarify the architecture before we begin execution:

### 1. Tech Stack / Language for Backend

- **Unified Python Backend:** The backend core (save parser, SQLite data layer, query engine, and API) will be built in Python using FastAPI/Uvicorn.
- **CLI Wrapper:** The CLI (`palengine`) will be a Python-based executable or script wrapper that interfaces directly with the backend core or API.

### 2. Palworld Save Tools Dependency

- Start by evaluating `palworld-save-tools` (or importing its parsing modules directly).
- Make sure to target specific parameter maps (e.g., `CharacterSaveParameterMap` and `BaseCampSaveData`) to parse only what is necessary in memory. Fall back to faster native bindings (`palsav`) only if performance or memory usage becomes a blocking issue.

### 3. Web UI Serving

- **Hybrid Approach:** FastAPI will serve the compiled React/Vite static assets for production/local use. For active development, running a Vite dev server that proxies/talks to the FastAPI backend on another port is fine.

### 4. CLI Output Format

- **Default Output:** Formatted ASCII / Markdown tables for human and agent readability.
- **JSON Option:** Provide a `--json` flag to return machine-readable raw JSON streams.

### 5. Breeding Logic Scope

- **Yes, Multi-Generational:** The breeding engine should compute multi-step breeding chains (parent -> child -> grandchild paths) to find valid breeding paths across multiple generations using owned Pals.

### 6. Save File Location & Discovery

- **Both:** Implement auto-discovery targeting standard local paths (e.g., `%LOCALAPPDATA%\Pal\Saved\SaveGames\<SteamID>\<SaveID>\Level.sav`), while allowing an optional `--save-path` flag/setting for manual overrides or custom save folders.

### 7. Palworld Version Scope

- **Extensible Architecture:** Treat `1.0` as the baseline, but design data schemas, parsers, and database models to be easily expandable for future game updates without breaking existing features.

### 8. Existing Project State

- **Greenfield:** Confirmed. There is no existing code or data in `c:\AI\palopedix`.
