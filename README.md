# Palopedix

Palopedix is an advanced save parser, analytics engine, and database viewer for **Palworld**. It provides an interactive web interface, a robust FastAPI backend, and a comprehensive CLI designed for AI agents and players to inspect, optimize, and plan gameplay.

---

## Key Features

- **Paldex & Skills Catalog**: Explore stats, elements, partner skills, active skills, passives, work suitabilities, and **18 deterministic Partner Skill categories** (Flying Mounts, Ranch Producers, Player Infusions, Artillery, Healers, Combat Buffs, etc.).
- **Save Game Parser & World Manager**: Auto-discovers Palworld save games (`Level.sav`), supports multi-world save switching, and decodes caught Pals, IVs, souls, ranks, and inventory.
- **Base Camp Work Crew Optimizer**: Analyzes placed infrastructure in active base camps, calculates work suitability demand, balances food consumption and SAN decay, and recommends optimal 24/7 Pal crews.
- **Multi-Generation Breeding Path Finder**: BFS pathfinding from owned Pals to any target Pal, complete with parent instance quality scoring, target passive skill preservation, and gender probability calculations.
- **Boss Counter-Party Recommender**: Builds optimal 5-Pal counter teams for Tower Bosses, Alpha Field Bosses, and Legendaries across three combat archetypes (Pure Elemental DPS, Mounted Player Infusion, and Balanced Hybrid Survival).
- **Pal Condenser Planner**: Evaluates duplicate Pal counts to pinpoint the highest-value condensing candidates and identifies optimal "Keeper" base Pals based on IVs and passives.
- **Items, Crafting & Tech Tree**: Browse equipment, spheres, materials, exact crafting recipes, and ancient technology unlocks.
- **Agent-First CLI**: Complete programmatic command-line interface with `--format json` output designed for AI agent integration.

---

## Project Structure

```
palopedix/
├── palengine/                 # Python backend package
│   ├── analytics/             # Optimizer, Boss Recommender & Investment algorithms
│   ├── api/                   # FastAPI REST server & endpoints
│   ├── cli/                   # Click CLI entry point (palengine/cli/main.py)
│   ├── db/                    # SQLite engine & database query layer
│   ├── parser/                # Level.sav GVAS decoding & entity extraction
│   └── world_manager.py       # Multi-world save discovery & switching
├── ui/                        # Modern React + Vite frontend web app
├── data/                      # Master SQLite database & static datasets
├── tests/                     # Automated pytest test suite
├── cli_commands.md            # Comprehensive CLI reference guide
├── PALOPEDIX_AGENT_GUIDE.md   # Mandatory operating guide for AI coding agents
└── AGENTS.md                  # Workspace agent configuration
```

---

## Running the Application

### 1. Backend REST API
```bash
# Start FastAPI backend server on port 8000
python -m uvicorn palengine.api.main:app --reload --port 8000
```

### 2. Frontend Web Interface
```bash
cd ui
npm install
npm run dev
```
Open your browser to `http://localhost:5173`.

### 3. CLI (Command Line / AI Agent Tooling)
```bash
# General CLI help
python -m palengine.cli.main --help

# Query static Pals
python -m palengine.cli.main pals -e Dragon -s mining:3

# Recommend boss counter party (JSON output for AI agents)
python -m palengine.cli.main --format json boss-party "Victor & Shadowbeak"

# Optimize base camp work crew
python -m palengine.cli.main --format json base --id <BASE_CAMP_ID> --recommend

# Find breeding paths
python -m palengine.cli.main --format json breed_path -o "Lamball,Cattiva" "Shadowbeak"
```

---

## Running Tests

Execute the automated test suite:
```bash
python -m pytest tests -v
```
