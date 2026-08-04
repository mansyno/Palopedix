import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from palengine.db.sqlite_engine import SQLiteEngine

def main():
    db = SQLiteEngine()
    candidates = db.get_condense_candidates()

    if not candidates:
        print("No pals found in database. Please load a save file in the UI or via CLI.")
        return

    print("Top candidates for condensing (based on amount of duplicates, passives, and IVs):")
    
    md_output = ["# Top Candidates for Condensing\n\nThis list highlights your best candidates based on duplicates, passives, and IVs.\n\n---\n"]
    
    for i, c in enumerate(candidates, 1):
        species = c['species']
        total_owned = c['total_owned']
        sacrifices = c['sacrifices_available']
        stars = c['attainable_stars']
        
        lvl = c['base_level']
        iv_hp = c['iv_hp']
        iv_atk = c['iv_attack']
        iv_def = c['iv_defense']
        passives_list = c['passives']
        passives_str = ', '.join(passives_list) if passives_list else 'None'
        
        est_hp = c['hp']
        est_atk = c['attack']
        est_def = c['defense']

        print(f"{i}. {species} - Total Owned: {total_owned} (1 Base + {sacrifices} Sacrifices available)")
        print(f"   Max Attainable Rank: {stars} Stars")
        print(f"   Best base candidate: Level {lvl}")
        print(f"   Calculated Display Stats (HP/Atk/Def): {est_hp} / {est_atk} / {est_def}")
        print(f"   Hidden IVs (HP/Atk/Def): {iv_hp} / {iv_atk} / {iv_def}")
        print(f"   Passives: {passives_str}")
        
        md_output.append(f"### {i}. **{species}**")
        md_output.append(f"*You currently have **{total_owned}** total owned (1 Base + **{sacrifices}** Sacrifices available).*\n")
        md_output.append(f"**Max Attainable Rank:** {'⭐' * stars if stars > 0 else '0 ⭐'}\n")
        md_output.append("| Stat | Value |")
        md_output.append("|---|---|")
        md_output.append(f"| **Best Base Candidate Level** | {lvl} |")
        md_output.append(f"| **Calculated Display Stats (HP/Atk/Def)** | {est_hp} / {est_atk} / {est_def} |")
        md_output.append(f"| **Hidden IVs (HP/Atk/Def)** | {iv_hp} / {iv_atk} / {iv_def} |")
        md_output.append(f"| **Passives** | `{passives_str}` |\n")
        md_output.append("---\n")

    artifact_path = os.path.join(os.environ.get('APPDATA_DIR', ''), 'brain', os.environ.get('CONVERSATION_ID', ''), 'top_condensing_pals.md')
    if os.path.exists(os.path.dirname(artifact_path)):
        with open(artifact_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_output))
    else:
        with open('top_condensing_pals.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_output))
            
    print("\nUpdated top_condensing_pals.md successfully!")

if __name__ == '__main__':
    main()
