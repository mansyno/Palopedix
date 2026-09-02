---
name: palworld-boss-recommender
description: >
  Recommends the single optimal 5-Pal counter-party for any Palworld Boss encounter (Tower Bosses, Alpha Field Bosses / Legendaries, and Dungeon Alphas).
  Analyzes actual player save game data, elemental advantages, mount damage infusion, combat buffers (Gobfin/Vanguard), per-Pal active skill movesets, and evaluates encounter beatability / arena time limit viability.
  Trigger when the user asks for the best team, party, strategy, or counters to defeat a specific Palworld boss.
---

# Palworld Boss Counter Party Recommender

This skill enables Antigravity to analyze a player's actual save game database to determine encounter beatability, arena time limit viability, and construct the single optimal 5-Pal counter-party for any Boss encounter.

---

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

## Core Operating Rules for the Agent

### 1. Strict Tool-Only Data Gathering (Zero Ad-Hoc Scripts)
- **Mandatory Tool Usage**: You MUST ALWAYS use the existing application CLI or Python engine methods to retrieve data.
  ```bash
  python -m palengine.cli.main --format json boss-party "<Boss Name>"
  ```
  Or to inspect caught instances directly:
  ```bash
  python -m palengine.cli.main --format json instances [-s Species] [-l party|palbox|base] [--min-level N]
  ```
- **Prohibited Actions**:
  - NEVER write ad-hoc Python scripts or temporary scratch parsers in the workspace.
  - NEVER attempt to decompress, parse, or extract `.sav` files manually. The SQLite database already contains all parsed and structured data.
- **Missing Data Protocol**: If requested data (such as specific equipped weapons or armor tiers) is not populated or available in the SQLite database, you MUST explicitly state that this data is missing before presenting your report.

### 2. Strict Data Integrity & Zero Hallucination
- Every single stat reported (Pal Species, Level, Star Rank, IVs, Passives, Mastered Waza, Location) MUST strictly match an exact queried record from the save database.
- NEVER invent hypothetical or inflated levels (e.g., do NOT recommend a "Lv.55 Anubis" if the player's actual Anubis in SQLite is Lv.30 or if no Anubis is owned).

### 3. Boss Beatability & Arena Timer Viability Assessment
- Boss encounters have distinct level requirements and arena timers (e.g. Tower Bosses enforce a strict 10-minute / 600s time limit):
  - **Required DPS Check**: For timed encounters, compare Boss HP against the time limit (`Required DPS = Boss HP / Time Limit in Seconds`).
  - **Level Scaling Assessment**: Calculate the level gap between the player's highest counter Pal and the Boss (`Level Gap = Pal Level - Boss Level`).
  - **Readiness Classification**:
    - 🟢 **FAVORED**: Lead Pal matches or exceeds Boss level (Level gap ≥ 0) with super-effective typing.
    - 🟡 **CHALLENGING**: Lead Pal is within 1–5 levels below Boss. Viable with active staggering and manual dodging.
    - 🟠 **HIGH DIFFICULTY**: Lead Pal is 6–9 levels below Boss. Severe damage reduction and incoming damage amplification.
    - 🔴 **UNLIKELY / NOT RECOMMENDED**: Lead Pal is ≥10 levels below Boss, or lacks elemental advantage.
- If the encounter is deemed **HIGH DIFFICULTY** or **UNLIKELY**, explicitly warn the user upfront:
  > `⚠️ ENCOUNTER READINESS: NOT RECOMMENDED AT CURRENT PROGRESSION`
  > State the exact level gap, the high risk of timing out during the DPS check, and the recommended level/condensing thresholds before attempting.

### 4. Single Optimal Party Recommendation (No Multi-Archetype Confusion)
- Recommend exactly **ONE** optimal 5-Pal team composed of the best possible combination from the player's actual owned roster:
  - **Slot 1 (Lead DPS & Elemental Infusion Mount)**: Best super-effective attacker or mount converter matching boss weakness.
  - **Slot 2 (Secondary DPS / Aggro Switch)**: High combat score counter or resilient off-tank for swapping during boss cooldowns.
  - **Slots 3–5 (Combat Buffers & Synergy)**: Best available Gobfins (player attack stack), Vanguard/Stronghold buffers, or secondary elemental counters.

### 5. Per-Pal Tailored Movesets (Waza) & Optimal Passives
- For each of the 5 recommended Pals in the party, provide:
  - **Assigned Active Skills (Waza)**: 3 specific moves (1 low CT ≤7s for stagger, 1 mid CT 8–25s for sustained DPS, 1 high power nuke ≥26s matching the boss's weakness or Pal's STAB).
  - **Target Passive Traits**: List the ideal passive loadout tailored to that specific Pal's role (e.g. `Ferocious, Musclehead, Legend, Burly Body` for Main DPS vs `Vanguard, Stronghold Strategist, Noble, Fine Coat` for Buffers).

### 6. No Breeding Fallbacks
- Do NOT output breeding project suggestions or multi-generation breeding paths. Recommendations must strictly focus on the player's current playable roster.

---

## Standard Output Format

When delivering boss counter recommendations to the user, follow this structure:

1. **Boss Profile & Encounter Constraints**:
   - Canonical Name, Location, Level, HP, Elements & Weaknesses.
   - Arena Time Limit (e.g., 10 minutes) and Required Sustained DPS threshold.
   - Dangerous attacks to watch out for.

2. **Encounter Readiness & Viability Verdict**:
   - Readiness status badge (🟢 FAVORED / 🟡 CHALLENGING / 🟠 HIGH DIFFICULTY / 🔴 UNLIKELY).
   - Clear verdict on whether the boss is currently beatable with the player's progression.
   - Timeout and DPS check analysis.

3. **Optimal 5-Pal Counter Party Table**:
   - Columns: `#`, `Role`, `Pal & Gender`, `Level & Rank`, `Element`, `Location`, `Current Passives`, `IVs (HP/Atk/Def)`.

4. **Per-Pal Moveset (Waza) & Passive Strategy**:
   - Detailed 3-skill active loadout (Name, Element, Power, Cooldown) and optimal target passives for each team member.

5. **Tactical Strategy**:
   - Pillar line-of-sight positioning, signature attack telegraphs, and Pal recall dodge timing.
