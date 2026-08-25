---
name: palworld-boss-recommender
description: >
  Recommends optimal 5-Pal counter-parties for any Palworld Boss encounter (Tower Bosses, Alpha Field Bosses / Legendaries, and Dungeon Alphas).
  Analyzes player save game data, elemental advantages, mount damage infusion, player attack buffers (Gobbfin/Vanguard), and breeding fallbacks.
  Trigger when the user asks for the best team, party, strategy, or counters to defeat a specific Palworld boss.
---

# Palworld Boss Counter Party Recommender

This skill enables Antigravity to analyze a player's actual save game data and static database to construct 3 optimized 5-Pal party archetypes for any 5-Pal Boss encounter.

## When to Use
- User asks: "Help me make a party to beat [Boss Name]"
- User asks: "What is the best team for [Tower Boss / Alpha Pal / Legendary]?"
- User asks: "How do I counter [Boss Name] with the Pals I currently own?"
- Applicable to:
  - **Tower Bosses**: Zoe & Grizzbolt, Lily & Lyleen, Axel & Orserk, Marcus & Faleris, Victor & Shadowbeak, Saya & Selyne.
  - **Alpha Field Bosses & Legendaries**: Frostallion, Jetragon, Necromus, Paladius, Blazamut, Astegon, Kingpaca, Mammorest, etc.
  - **Dungeon / Oil Rig Alphas**.
- **Note**: Does NOT apply to 15–20 Base Summoning Altar Raids (Bellanoir/Blazamut Ryu base raids).

---

## Standard Workflow

### Step 1: Execute Boss Party Analyzer
Run the built-in CLI tool or import the module directly:

```bash
python -m palengine.cli.main boss-party "<Boss Name>"
```
Or for raw structured JSON output:
```bash
python -m palengine.cli.main --format json boss-party "<Boss Name>"
```

### Step 2: Present the Recommendations Clearly
When presenting the party recommendations to the user, ensure all of the following rules are respected:

1. **Human-Visible Identification**:
   - Never output raw IDs or GUIDs.
   - Always state: `Species`, `Gender (♂/♀)`, `Level`, `Rank (★)`, and `Passive Skills` so duplicates of the same level can be clearly differentiated.

2. **Accurate Location Tagging**:
   - State whether the Pal is in `Palbox`, `In Party`, or `Base: [Base Name]`.

3. **Present 3 Distinct Archetypes**:
   - **Option A: Pure Pal Elemental DPS** (Super-effective direct counters with high combat stats).
   - **Option B: Mounted Player-DPS Build** (Elemental infusion mount matching boss weakness + Gobfin/Vanguard damage stack).
   - **Option C: Balanced Hybrid & Survival** (Damage sponge tank + elemental attacker + Vanguard/Stronghold buffers).

4. **Movesets (Waza)**:
   - Provide recommended active skills with low cooldowns (CT ≤ 5s for staggering) and high burst power.

5. **Breeding Fallbacks (Tier 3)**:
   - If the player is missing high-level counters, show breeding paths from their owned stock, explicitly marked with:
     `⚠️ Hatches at Level 1 (Requires EXP training / Training Manuals before the fight)`.

6. **Tactical Strategy**:
   - Highlight arena pillar line-of-sight mechanics, lethal boss telegraphs (e.g. Divine Disaster, Kerauno, Phoenix Flare), and pal recall dodge timing.
