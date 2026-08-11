# PalEngine CLI Commands Reference

This document provides a reference for the available CLI commands in the PalEngine application.

The CLI tool can be run using the `palengine/cli/main.py` entry point. It supports standard options like `--format` (`table` or `json`).

## Commands

- **`pals`**: Queries the static Paldex database.
  - Options include filtering by element (`--element`), nocturnal habits (`--nocturnal`), work suitability (`--suitability`), and size (`--size`).

- **`instances`**: Queries dynamic Pal instances from the save game.
  - Requires or auto-discovers a `Level.sav` save file.
  - Options include filtering by location, species, gender, minimum level, minimum IVs, and passive skills.

- **`bases`**: Summarizes player Base Camps and placed structures.
  - Requires or auto-discovers a save file and provides an overview of the base, workers, and infrastructure.

- **`breed`**: Calculates the breeding child of two parents.
  - Takes two parent names as arguments and returns the resulting child species.

- **`breed_path`**: Finds the shortest BFS breeding path from owned species to a target Pal.
  - Takes a comma-separated list of currently owned Pals and the target Pal, returning step-by-step breeding instructions.

- **`base`**: Manages base camp analytics and optimal Pal team recommendations.
  - Can list active base camps, generate optimal Pal recommendations for a base camp (`--recommend`), and show base camp structures.
