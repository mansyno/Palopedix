"""Pal Soul Crusher Optimizer.

Calculates current Pal Soul inventory across player storage (inventory and chests),
evaluates direct stat maxing capacity vs. optimal Crusher conversions (2:1 ratio),
and provides step-by-step Crusher instructions to maximize maxable Pal stats.
"""

from typing import Any

# Internal Palworld item IDs mapped to standard soul names
SOUL_ITEM_MAP: dict[str, str] = {
    "palupgradestone": "small",
    "palupgradestone2": "medium",
    "palupgradestone3": "large",
    "palupgradestone4": "giant",
}

SOUL_DISPLAY_NAMES: dict[str, str] = {
    "small": "Small Pal Soul",
    "medium": "Medium Pal Soul",
    "large": "Large Pal Soul",
    "giant": "Giant Pal Soul",
}

# Souls required to upgrade one stat from Rank 0 to 20 at Statue of Power
SOUL_COST_PER_STAT: dict[str, int] = {
    "small": 10,   # Ranks 1–4: 1 + 2 + 3 + 4
    "medium": 6,   # Ranks 5–7: 1 + 2 + 3
    "large": 6,    # Ranks 8–10: 1 + 2 + 3
    "giant": 30,   # Ranks 11–20: 1+2+2+3+3+3+4+4+4+4
}

# Multiplier in Small Pal Soul equivalents (2:1 bidirectional Crusher ratio)
SOUL_WEIGHTS: dict[str, int] = {
    "small": 1,
    "medium": 2,
    "large": 4,
    "giant": 8,
}

# 10*1 + 6*2 + 6*4 + 30*8 = 10 + 12 + 24 + 240 = 286
TOTAL_SMALL_EQUIVALENT_PER_STAT = 286


def calculate_direct_maxable_stats(inventory: dict[str, int]) -> int:
    """Calculates how many stats can be maxed without any Crusher conversion."""
    s = inventory.get("small", 0)
    m = inventory.get("medium", 0)
    l = inventory.get("large", 0)
    g = inventory.get("giant", 0)

    return min(
        s // SOUL_COST_PER_STAT["small"],
        m // SOUL_COST_PER_STAT["medium"],
        l // SOUL_COST_PER_STAT["large"],
        g // SOUL_COST_PER_STAT["giant"],
    )


def solve_crusher_plan(
    current: dict[str, int], target_stats: int
) -> tuple[bool, list[dict[str, Any]], dict[str, int]]:
    """Attempts to satisfy target_stats maxed stats using 2:1 Crusher conversions.

    Returns:
        (is_feasible, steps_list, final_inventory)
    """
    if target_stats <= 0:
        return True, [], dict(current)

    req = {
        "small": target_stats * SOUL_COST_PER_STAT["small"],
        "medium": target_stats * SOUL_COST_PER_STAT["medium"],
        "large": target_stats * SOUL_COST_PER_STAT["large"],
        "giant": target_stats * SOUL_COST_PER_STAT["giant"],
    }

    cur_s = current.get("small", 0)
    cur_m = current.get("medium", 0)
    cur_l = current.get("large", 0)
    cur_g = current.get("giant", 0)

    steps: list[dict[str, Any]] = []

    # 1. UPWARD CONVERSION (Combine lower tiers into higher tiers when surplus exists)
    # Small -> Medium
    if cur_s > req["small"]:
        surplus_s = cur_s - req["small"]
        can_convert_s = (surplus_s // 2) * 2
        if can_convert_s > 0:
            m_gained = can_convert_s // 2
            cur_s -= can_convert_s
            cur_m += m_gained
            steps.append({
                "action": "combine",
                "from_tier": "small",
                "to_tier": "medium",
                "from_name": SOUL_DISPLAY_NAMES["small"],
                "to_name": SOUL_DISPLAY_NAMES["medium"],
                "input_count": can_convert_s,
                "output_count": m_gained,
                "description": f"Convert {can_convert_s} Small Pal Souls into {m_gained} Medium Pal Souls at Crusher",
            })

    # Medium -> Large
    if cur_m > req["medium"]:
        surplus_m = cur_m - req["medium"]
        can_convert_m = (surplus_m // 2) * 2
        if can_convert_m > 0:
            l_gained = can_convert_m // 2
            cur_m -= can_convert_m
            cur_l += l_gained
            steps.append({
                "action": "combine",
                "from_tier": "medium",
                "to_tier": "large",
                "from_name": SOUL_DISPLAY_NAMES["medium"],
                "to_name": SOUL_DISPLAY_NAMES["large"],
                "input_count": can_convert_m,
                "output_count": l_gained,
                "description": f"Convert {can_convert_m} Medium Pal Souls into {l_gained} Large Pal Souls at Crusher",
            })

    # Large -> Giant
    if cur_l > req["large"] and cur_g < req["giant"]:
        needed_g = req["giant"] - cur_g
        needed_l_for_g = needed_g * 2
        surplus_l = cur_l - req["large"]
        convert_l = min(surplus_l, needed_l_for_g)
        convert_l = (convert_l // 2) * 2
        if convert_l > 0:
            g_gained = convert_l // 2
            cur_l -= convert_l
            cur_g += g_gained
            steps.append({
                "action": "combine",
                "from_tier": "large",
                "to_tier": "giant",
                "from_name": SOUL_DISPLAY_NAMES["large"],
                "to_name": SOUL_DISPLAY_NAMES["giant"],
                "input_count": convert_l,
                "output_count": g_gained,
                "description": f"Convert {convert_l} Large Pal Souls into {g_gained} Giant Pal Souls at Crusher",
            })

    # 2. DOWNWARD CONVERSION (Shatter higher tiers into lower tiers if deficits exist)
    # Giant -> Large
    if cur_g > req["giant"]:
        surplus_g = cur_g - req["giant"]
        needed_below_l = max(0, req["large"] - cur_l)
        needed_below_m = max(0, req["medium"] - cur_m)
        needed_below_s = max(0, req["small"] - cur_s)
        total_l_needed = needed_below_l + (needed_below_m + 1) // 2 + (needed_below_s + 3) // 4
        shatter_g = min(surplus_g, (total_l_needed + 1) // 2)
        if shatter_g > 0:
            l_gained = shatter_g * 2
            cur_g -= shatter_g
            cur_l += l_gained
            steps.append({
                "action": "shatter",
                "from_tier": "giant",
                "to_tier": "large",
                "from_name": SOUL_DISPLAY_NAMES["giant"],
                "to_name": SOUL_DISPLAY_NAMES["large"],
                "input_count": shatter_g,
                "output_count": l_gained,
                "description": f"Shatter {shatter_g} Giant Pal Souls into {l_gained} Large Pal Souls at Crusher",
            })

    # Large -> Medium
    if cur_l > req["large"]:
        surplus_l = cur_l - req["large"]
        needed_below_m = max(0, req["medium"] - cur_m)
        needed_below_s = max(0, req["small"] - cur_s)
        total_m_needed = needed_below_m + (needed_below_s + 1) // 2
        shatter_l = min(surplus_l, (total_m_needed + 1) // 2)
        if shatter_l > 0:
            m_gained = shatter_l * 2
            cur_l -= shatter_l
            cur_m += m_gained
            steps.append({
                "action": "shatter",
                "from_tier": "large",
                "to_tier": "medium",
                "from_name": SOUL_DISPLAY_NAMES["large"],
                "to_name": SOUL_DISPLAY_NAMES["medium"],
                "input_count": shatter_l,
                "output_count": m_gained,
                "description": f"Shatter {shatter_l} Large Pal Souls into {m_gained} Medium Pal Souls at Crusher",
            })

    # Medium -> Small
    if cur_m > req["medium"] and cur_s < req["small"]:
        surplus_m = cur_m - req["medium"]
        needed_s = req["small"] - cur_s
        shatter_m = min(surplus_m, (needed_s + 1) // 2)
        if shatter_m > 0:
            s_gained = shatter_m * 2
            cur_m -= shatter_m
            cur_s += s_gained
            steps.append({
                "action": "shatter",
                "from_tier": "medium",
                "to_tier": "small",
                "from_name": SOUL_DISPLAY_NAMES["medium"],
                "to_name": SOUL_DISPLAY_NAMES["small"],
                "input_count": shatter_m,
                "output_count": s_gained,
                "description": f"Shatter {shatter_m} Medium Pal Souls into {s_gained} Small Pal Souls at Crusher",
            })

    # Check if all requirements are satisfied
    is_feasible = (
        cur_s >= req["small"]
        and cur_m >= req["medium"]
        and cur_l >= req["large"]
        and cur_g >= req["giant"]
    )

    final_inventory = {
        "small": cur_s,
        "medium": cur_m,
        "large": cur_l,
        "giant": cur_g,
    }

    return is_feasible, steps, final_inventory


def optimize_pal_souls(inventory: dict[str, int]) -> dict[str, Any]:
    """Optimizes Pal Soul allocation and generates step-by-step Crusher instructions.

    Args:
        inventory: dict with keys 'small', 'medium', 'large', 'giant'

    Returns:
        Detailed optimization result dict.
    """
    s = inventory.get("small", 0)
    m = inventory.get("medium", 0)
    l = inventory.get("large", 0)
    g = inventory.get("giant", 0)

    direct_maxable = calculate_direct_maxable_stats(inventory)

    # Calculate theoretical max using small equivalents
    total_small_eq = (
        s * SOUL_WEIGHTS["small"]
        + m * SOUL_WEIGHTS["medium"]
        + l * SOUL_WEIGHTS["large"]
        + g * SOUL_WEIGHTS["giant"]
    )
    upper_bound = total_small_eq // TOTAL_SMALL_EQUIVALENT_PER_STAT

    # Search downward from theoretical upper bound to find exact achievable stats
    optimal_stats = 0
    best_steps: list[dict[str, Any]] = []
    final_inv = dict(inventory)

    for candidate in range(upper_bound, -1, -1):
        feasible, steps, resulting_inv = solve_crusher_plan(inventory, candidate)
        if feasible:
            optimal_stats = candidate
            best_steps = steps
            final_inv = resulting_inv
            break

    # Calculate leftover remainder after upgrading optimal_stats
    required_for_optimal = {
        "small": optimal_stats * SOUL_COST_PER_STAT["small"],
        "medium": optimal_stats * SOUL_COST_PER_STAT["medium"],
        "large": optimal_stats * SOUL_COST_PER_STAT["large"],
        "giant": optimal_stats * SOUL_COST_PER_STAT["giant"],
    }
    remainder = {
        tier: max(0, final_inv[tier] - required_for_optimal[tier])
        for tier in ("small", "medium", "large", "giant")
    }

    gain_stats = optimal_stats - direct_maxable

    return {
        "current_inventory": {
            "small": s,
            "medium": m,
            "large": l,
            "giant": g,
        },
        "total_small_equivalents": total_small_eq,
        "direct_maxable_stats": direct_maxable,
        "direct_pals_maxed": direct_maxable // 4,
        "optimal_maxable_stats": optimal_stats,
        "optimal_pals_maxed": optimal_stats // 4,
        "stats_gained_via_crusher": gain_stats,
        "crusher_steps": best_steps,
        "projected_inventory": final_inv,
        "required_for_optimal": required_for_optimal,
        "remainder_after_optimal": remainder,
    }
