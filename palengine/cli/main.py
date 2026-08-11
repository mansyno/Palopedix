"""CLI wrapper for PalEngine using click.

Supports markdown tables and raw JSON output formats.
"""

import glob
import json
import os
from typing import Any, Optional

import click
from tabulate import tabulate

from palengine.db.sqlite_engine import SQLiteEngine


def discover_save_path() -> Optional[str]:
    """Auto-discovers the most recently modified Level.sav file in LocalAppData."""
    local_appdata = os.getenv("LOCALAPPDATA")
    if not local_appdata:
        return None
    save_games_dir = os.path.join(local_appdata, "Pal", "Saved", "SaveGames")
    if not os.path.isdir(save_games_dir):
        return None

    # Search recursively for Level.sav files
    search_pattern = os.path.join(save_games_dir, "**", "Level.sav")
    level_sav_files = glob.glob(search_pattern, recursive=True)

    if not level_sav_files:
        return None

    # Return the file with the latest modification time
    try:
        return max(level_sav_files, key=os.path.getmtime)
    except Exception:
        return None


def get_resolved_save_path(save_path: Optional[str]) -> str:
    """Returns the provided save_path or attempts auto-discovery."""
    if save_path:
        if not os.path.isfile(save_path):
            raise click.ClickException(f"Save file not found at: {save_path}")
        return save_path

    discovered = discover_save_path()
    if not discovered:
        raise click.ClickException(
            "Could not auto-discover Level.sav. Please specify --save-path explicitly."
        )
    return discovered


def format_output(data: Any, format_type: str, headers: str = "keys") -> str:
    """Formats Python data structures as table or JSON string."""
    if format_type == "json":
        return json.dumps(data, indent=2)
    else:
        if not data:
            return "No results found."
        if isinstance(data, list):
            # Convert dict structures for cleaner table display
            table_data = []
            for row in data:
                row_copy = dict(row)
                # Flatten nested dicts / lists for clean printing
                for k, v in row_copy.items():
                    if isinstance(v, (dict, list)):
                        row_copy[k] = str(v)
                table_data.append(row_copy)
            return tabulate(table_data, headers=headers, tablefmt="github")
        elif isinstance(data, dict):
            return tabulate(
                [(k, str(v)) for k, v in data.items()],
                headers=["Property", "Value"],
                tablefmt="github",
            )
        return str(data)


@click.group()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output formatting style.",
)
@click.pass_context
def cli(ctx: click.Context, format: str) -> None:
    """PalEngine CLI tool for querying static Paldex and dynamic save file data."""
    ctx.ensure_object(dict)
    ctx.obj["format"] = format
    ctx.obj["engine"] = SQLiteEngine()


@cli.command()
@click.option("--element", "-e", help="Filter by element type.")
@click.option(
    "--nocturnal",
    "-n",
    is_flag=True,
    default=None,
    help="Filter by nocturnal nocturnal habits.",
)
@click.option(
    "--suitability",
    "-s",
    help="Filter by work suitability and min level in 'name:level' format (e.g. handiwork:3).",
)
@click.option("--size", type=click.Choice(["XS", "S", "M", "L", "XL"]), help="Filter by size.")
@click.pass_context
def pals(
    ctx: click.Context,
    element: Optional[str],
    nocturnal: Optional[bool],
    suitability: Optional[str],
    size: Optional[str],
) -> None:
    """Queries the static Paldex database."""
    engine: SQLiteEngine = ctx.obj["engine"]
    filters: dict[str, Any] = {}

    if element:
        filters["element"] = element.capitalize()
    if nocturnal is not None:
        filters["nocturnal"] = nocturnal
    if size:
        filters["size"] = size

    if suitability:
        if ":" in suitability:
            name, min_lvl = suitability.split(":", 1)
            filters["work_suitability"] = {"name": name.lower(), "min_level": int(min_lvl)}
        else:
            filters["work_suitability"] = {"name": suitability.lower(), "min_level": 1}

    results = engine.query_pals(filters)

    # Clean display fields for CLI printing
    display_results = []
    for r in results:
        display_results.append(
            {
                "Paldex #": r["paldex_number"],
                "Name": r["display_name"],
                "Elements": "/".join(filter(None, [r["element_1"], r["element_2"]])),
                "Breeding Power": r["breeding_power"],
                "Nocturnal": "Yes" if r["nocturnal"] else "No",
                "Size": r["size"],
            }
        )

    click.echo(format_output(display_results, ctx.obj["format"]))


@cli.command()
@click.option("--save-path", "-p", help="Path to Level.sav file.")
@click.option("--location", "-l", type=click.Choice(["party", "palbox", "base"]), help="Location filter.")
@click.option("--species", "-s", help="Filter by species display name.")
@click.option("--gender", "-g", type=click.Choice(["Male", "Female"]), help="Gender filter.")
@click.option("--min-level", type=int, help="Minimum Pal level.")
@click.option(
    "--min-iv",
    help="Filter by minimum IV in 'stat:value' format (e.g. melee:70, defense:80).",
)
@click.option("--passive", help="Filter by passive skill ID.")
@click.pass_context
def instances(
    ctx: click.Context,
    save_path: Optional[str],
    location: Optional[str],
    species: Optional[str],
    gender: Optional[str],
    min_level: Optional[int],
    min_iv: Optional[str],
    passive: Optional[str],
) -> None:
    """Queries dynamic Pal instances from the save game."""
    engine: SQLiteEngine = ctx.obj["engine"]
    resolved_path = get_resolved_save_path(save_path)

    # Load save data
    engine.load_save_data(resolved_path)

    filters: dict[str, Any] = {}
    if location:
        filters["location"] = location
    if species:
        filters["species"] = species
    if gender:
        filters["gender"] = gender
    if min_level:
        filters["min_level"] = min_level
    if passive:
        filters["passive_id"] = passive

    if min_iv and ":" in min_iv:
        stat, val = min_iv.split(":", 1)
        filters[f"min_iv_{stat.lower()}"] = int(val)

    results = engine.query_instances(filters)

    display_results = []
    for r in results:
        passives_list = [p["name"] for p in r.get("passives", [])]
        display_results.append(
            {
                "Species": r["display_name"],
                "Level": r["level"],
                "Gender": r["gender"],
                "Rank": f"{r['rank']} Star" if r["rank"] > 0 else "0 Star",
                "IVs (HP/Atk/Def)": f"{r['iv_hp']}/{r['iv_melee']}/{r['iv_defense']}",
                "Location": r["location"].capitalize(),
                "Passives": ", ".join(passives_list) if passives_list else "None",
            }
        )

    click.echo(format_output(display_results, ctx.obj["format"]))


@cli.command()
@click.option("--save-path", "-p", help="Path to Level.sav file.")
@click.pass_context
def bases(ctx: click.Context, save_path: Optional[str]) -> None:
    """Summarizes player Base Camps and placed structures."""
    engine: SQLiteEngine = ctx.obj["engine"]
    resolved_path = get_resolved_save_path(save_path)

    # Load save data
    engine.load_save_data(resolved_path)

    cursor = engine.conn.cursor()
    cursor.execute("SELECT base_camp_id, name FROM base_camps")
    base_rows = cursor.fetchall()

    if not base_rows:
        click.echo("No base camps found.")
        return

    display_results = []
    for base in base_rows:
        summary = engine.get_base_camp_summary(base["base_camp_id"])
        if summary:
            # Format worker summary
            workers_str = f"{len(summary['workers'])} Pals"
            # Format structure summary
            structs_summary = []
            for s in summary["structures"]:
                name = s["display_name"] or s["structure_name"]
                structs_summary.append(f"{s['count']}x {name}")
            structs_str = ", ".join(structs_summary) if structs_summary else "None"

            display_results.append(
                {
                    "Base Name": base["name"],
                    "Workers": workers_str,
                    "Infrastructure / Placed Structures": structs_str,
                }
            )

    click.echo(format_output(display_results, ctx.obj["format"]))


@cli.command()
@click.argument("parent1")
@click.argument("parent2")
@click.pass_context
def breed(ctx: click.Context, parent1: str, parent2: str) -> None:
    """Calculates the breeding child of two parents."""
    engine: SQLiteEngine = ctx.obj["engine"]
    child = engine.get_breeding_result(parent1, parent2)

    if not child:
        raise click.ClickException(
            f"Could not calculate breeding result for parents '{parent1}' and '{parent2}'."
        )

    display = {
        "Parent 1": parent1.capitalize(),
        "Parent 2": parent2.capitalize(),
        "Resulting Child": child["display_name"],
        "Paldex #": child["paldex_number"],
        "Child Breeding Power": child["breeding_power"],
        "Elements": "/".join(filter(None, [child["element_1"], child["element_2"]])),
    }
    click.echo(format_output(display, ctx.obj["format"]))


@cli.command()
@click.option(
    "--owned",
    "-o",
    required=True,
    help="Comma-separated list of currently owned Pal species (e.g. Lamball,Cattiva,Penking).",
)
@click.argument("target")
@click.pass_context
def breed_path(ctx: click.Context, owned: str, target: str) -> None:
    """Finds the shortest BFS breeding path from owned species to a target Pal."""
    engine: SQLiteEngine = ctx.obj["engine"]
    owned_list = [s.strip() for s in owned.split(",") if s.strip()]

    path = engine.find_breeding_path(owned_list, target)

    if not path:
        click.echo(
            f"No breeding path could be found from your owned Pals to target '{target}'."
        )
        return

    display_results = []
    for step_num, step in enumerate(path, 1):
        display_results.append(
            {
                "Step": f"Step {step_num}",
                "Parent 1": step["parent1"],
                "Parent 2": step["parent2"],
                "Produces Child": step["child"],
            }
        )

    click.echo(format_output(display_results, ctx.obj["format"]))


@cli.command()
@click.option("--id", "base_id", required=False, help="Target Base Camp ID.")
@click.option("--recommend", is_flag=True, help="Generates optimal Pal recommendations for base camp.")
@click.option("--max-team", type=int, default=None, help="Maximum recommended team size.")
@click.pass_context
def base(ctx: click.Context, base_id: Optional[str], recommend: bool, max_team: Optional[int]) -> None:
    """Manages base camp analytics and optimal Pal team recommendations."""
    engine: SQLiteEngine = ctx.obj["engine"]
    from palengine.analytics.pal_recommender import PalRecommender

    if not base_id:
        camps = engine.get_base_camps()
        if not camps:
            click.echo("No active base camps found in save data.")
            return
        if ctx.obj["format"] == "json":
            click.echo(json.dumps(camps, indent=2))
        else:
            click.echo(tabulate(camps, headers="keys", tablefmt="github"))
        return

    if recommend:
        recommender = PalRecommender(engine)
        result = recommender.recommend_pals_for_base(base_id, max_team_size=max_team)

        if ctx.obj["format"] == "json":
            click.echo(json.dumps(result, indent=2))
            return

        click.echo(f"=== Base Camp Optimization & Recommended Pals [{result['base_category']} Base] ===")
        click.echo(f"Base Camp ID: {base_id} | Team Capacity: {result['team_size']}/{result['max_capacity']}\n")

        team_display = []
        for idx, pal in enumerate(result["recommended_team"], 1):
            roles_str = ", ".join([f"{r['work_type']} Lv{r['level']}" for r in pal["matching_roles"]])
            passives_str = ", ".join(pal["passives"]) if pal["passives"] else "None"
            nocturnal_str = "Yes (24/7)" if pal["nocturnal"] else "No"
            team_display.append({
                "#": idx,
                "Species": pal["display_name"],
                "Level": pal["level"],
                "Nocturnal": nocturnal_str,
                "Passives": passives_str,
                "Work Roles": roles_str,
                "Score": pal["total_score"],
            })

        click.echo(tabulate(team_display, headers="keys", tablefmt="github"))
        
        fs = result["food_and_san_summary"]
        click.echo(f"\n--- Food & SAN Balance ---")
        click.echo(f"Hourly Satiety Drain: {fs['total_hourly_satiety_drain']} | Average SAN Decay Mult: {fs['average_san_decay_multiplier']} | SAN Status: {fs['san_stability_status']}")
        
        if result["uncovered_suitabilities"]:
            click.echo(f"\nWarning: Uncovered Work Suitabilities: {', '.join(result['uncovered_suitabilities'])}")
    else:
        summary = engine.get_base_camp_structures(base_id)
        click.echo(format_output(summary, ctx.obj["format"]))


if __name__ == "__main__":
    cli()
