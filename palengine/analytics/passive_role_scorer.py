"""Analytics module for 4-aspect passive role scoring (Work, Attack, Defense, Movement).

Evaluates Pal instances based on their actual role specializations using predefined point tables.
"""

from typing import Any, Optional

# ── Aspect Point Dictionaries ──────────────────────────────────────────────

WORK_PASSIVES: dict[str, int] = {
    "remarkable craftsmanship": 75,
    "artisan": 50,
    "ranch master": 40,
    "philanthropist": 35,
    "work slave": 30,
    "hermit sage": 30,
    "babysitter": 30,
    "world tree's bounty": 25,
    "world tree seedbed": 25,
    "insomnia": 25,
    "nocturnal": 20,
    "night owl": 15,
    "lucky": 20,
    "serious": 20,
    "heart of the immovable king": 20,
    "lavish hospitality": 20,
    "farmhand": 15,
    "workaholic": 15,
    "mastery of fasting": 12,
    "conceited": 10,
    "positive thinker": 10,
    "service-minded": 10,
    "diet lover": 10,
    "dainty eater": 8,
    "musclehead": -50,
    "slacker": -30,
    "clumsy": -10,
    "hooligan": -10,
}

ATTACK_PASSIVES: dict[str, int] = {
    "twin-edged holy blade": 50,
    "god of destruction": 40,
    "demon god": 30,
    "musclehead": 30,
    "divine dragon": 30,
    "ice emperor": 30,
    "ferocious": 20,
    "legend": 20,
    "lord of the underworld": 20,
    "celestial emperor": 20,
    "spirit emperor": 20,
    "lord of lightning": 20,
    "lord of the sea": 20,
    "earth emperor": 20,
    "flame emperor": 20,
    "siren of the void": 20,
    "immortality": 15,
    "lucky": 15,
    "hooligan": 15,
    "sadist": 15,
    "serenity": 15,
    "aggressive": 10,
    "brave": 10,
    # +10 Elemental Passives
    "blood of the dragon": 10,
    "coldblooded": 10,
    "pyromaniac": 10,
    "hydromaniac": 10,
    "botanist": 10,
    "capacitor": 10,
    "earth organ": 10,
    "dragonkiller": 10,
    "zen mind": 10,
    "veil of darkness": 10,
    "invader": 10,
    # Negative Attack
    "work slave": -30,
    "pacifist": -20,
    "masochist": -15,
    "coward": -10,
}

DEFENSE_PASSIVES: dict[str, int] = {
    "sanctified meat shield": 50,
    "diamond body": 35,
    "heavyweight": 22,
    "god of destruction": 20,
    "legend": 20,
    "burly body": 20,
    "immortality": 20,
    "masochist": 15,
    "lucky": 15,
    "hard skin": 10,
    "twin-edged holy blade": -30,
    "brittle": -20,
    "sadist": -15,
    "aggressive": -10,
    "conceited": -10,
    "downtrodden": -10,
}

MOVEMENT_PASSIVES: dict[str, int] = {
    "dimensional leap": 50,
    "swift": 30,
    "king of the waves": 30,
    "ace swimmer": 25,
    "eternal engine": 25,
    "skymarcher": 25,
    "legend": 20,
    "runner": 20,
    "infinite stamina": 20,
    "sleek stroke": 15,
    "lightfooted": 12,
    "nimble": 10,
    "fit as a fiddle": 10,
    "bottomless stomach": -8,
    "glutton": -5,
}


def _extract_passive_name(passive: Any) -> str:
    """Extracts a normalized lower-case passive name from a dict or string."""
    if isinstance(passive, dict):
        raw = str(passive.get("name") or passive.get("id") or "")
    else:
        raw = str(passive or "")
    return raw.strip().lower()


def calculate_passive_role_scores(passives: list[Any]) -> dict[str, Any]:
    """Calculates point totals for Work, Attack, Defense, and Movement.

    Args:
        passives: List of passive objects (dicts or strings).

    Returns:
        dict with keys:
            - 'score_work': int
            - 'score_attack': int
            - 'score_defense': int
            - 'score_movement': int
            - 'score_best': int (highest score among the 4 aspects)
            - 'best_role': str ('work' | 'attack' | 'defense' | 'movement')
            - 'role_breakdown': dict with point contributions per passive
    """
    score_work = 0
    score_attack = 0
    score_defense = 0
    score_movement = 0

    breakdown: dict[str, list[tuple[str, int]]] = {
        "work": [],
        "attack": [],
        "defense": [],
        "movement": [],
    }

    for p in passives:
        p_name = _extract_passive_name(p)
        if not p_name:
            continue

        # Human-readable title for UI breakdown
        p_title = (p.get("name") or p.get("id")) if isinstance(p, dict) else str(p)
        p_title = str(p_title).strip()

        w_pts = WORK_PASSIVES.get(p_name, 0)
        a_pts = ATTACK_PASSIVES.get(p_name, 0)
        d_pts = DEFENSE_PASSIVES.get(p_name, 0)
        m_pts = MOVEMENT_PASSIVES.get(p_name, 0)

        score_work += w_pts
        score_attack += a_pts
        score_defense += d_pts
        score_movement += m_pts

        if w_pts != 0:
            breakdown["work"].append((p_title, w_pts))
        if a_pts != 0:
            breakdown["attack"].append((p_title, a_pts))
        if d_pts != 0:
            breakdown["defense"].append((p_title, d_pts))
        if m_pts != 0:
            breakdown["movement"].append((p_title, m_pts))

    # Determine best role
    role_scores = {
        "work": score_work,
        "attack": score_attack,
        "defense": score_defense,
        "movement": score_movement,
    }

    # Pick the highest scoring role (default to 'work' if all 0 or tied)
    best_role = max(role_scores, key=lambda k: role_scores[k])
    best_score = role_scores[best_role]

    return {
        "score_work": score_work,
        "score_attack": score_attack,
        "score_defense": score_defense,
        "score_movement": score_movement,
        "score_best": best_score,
        "best_role": best_role,
        "role_scores": role_scores,
        "breakdown": breakdown,
    }
