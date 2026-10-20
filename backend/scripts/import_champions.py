"""
Script d'import des champions et de leurs spells depuis Data Dragon.
Usage : depuis le dossier backend/, lancer :
    python -m scripts.import_champions
"""

import sys
import os
import time
import certifi

# Fix Windows : force le bon chemin vers les certificats SSL
os.environ["SSL_CERT_FILE"] = certifi.where()

import httpx

# Ajoute le dossier parent (backend/) au path Python
# pour pouvoir importer app.database
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import get_connection

# --- CONFIG ---
DDRAGON_VERSION = "16.3.1"
BASE_URL = f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/data/fr_FR"


# --- TABLES DE MAPPING ---

# Convertit le "partype" de Data Dragon vers la colonne resource_type de ta BDD
RESOURCE_MAP = {
    "Mana": "mana",
    "Energy": "energy",
    "None": "none",
    "": "none",
    "Fury": "fury",
    "Rage": "rage",
    "Flow": "flow",
    "Ferocity": "ferocity",
    "Heat": "heat",
    "Shield": "shield",
    "Blood Well": "bloodwell",
    "Grit": "grit",
    "Courage": "courage",
    # Cas speciaux (certains champions ont des noms de ressource uniques)
    "Crimson Rush": "none",
    "Soul Unbound": "none",
    "Ammunition": "none",
}

# Mots-cles CC dans les descriptions de spells (en francais)
# On cherche ces mots dans le texte pour detecter si un spell a du CC
CC_KEYWORDS = {
    "étourdi": "stun",
    "immobilis": "root",
    "ralenti": "slow",
    "charme": "charm",
    "silence": "silence",
    "aveugl": "blind",
    "repouss": "knock_back",
    "projet": "knock_up",
    "suppression": "suppress",
    "terreur": "fear",
    "endort": "sleep",
    "provoque": "taunt",
    "enraciné": "root",
}


# --- FONCTIONS UTILITAIRES ---

def get_damage_type(tags, info):
    """Deduit le type de degats (AD/AP/Hybrid) a partir des tags et stats info."""
    has_mage = "Mage" in tags
    has_marksman = "Marksman" in tags

    # Cas simples
    if has_mage and not has_marksman:
        return "AP"
    if has_marksman and not has_mage:
        return "AD"
    # Si les deux tags sont presents → Hybrid
    if has_mage and has_marksman:
        return "Hybrid"

    # Sinon on regarde les stats info (attack vs magic)
    if info.get("magic", 0) >= 7:
        return "AP"
    return "AD"


def get_resource_type(partype):
    """Convertit le partype Data Dragon en resource_type pour la BDD."""
    return RESOURCE_MAP.get(partype, "none")


def get_attack_range(attack_range_value):
    """Melee si portee < 300, Ranged sinon."""
    return "Melee" if attack_range_value < 300 else "Ranged"


def detect_cc(description):
    """
    Detecte si un spell a du CC en cherchant des mots-cles dans la description.
    Retourne (is_cc: bool, type_cc: str ou None)
    """
    desc_lower = description.lower()
    for keyword, cc_type in CC_KEYWORDS.items():
        if keyword in desc_lower:
            return True, cc_type
    return False, None


def detect_spell_damage_type(description):
    """Detecte le type de degats d'un spell depuis sa description."""
    desc_lower = description.lower()
    has_magic = "dégâts magiques" in desc_lower or "dégâts mag" in desc_lower
    has_physical = "dégâts physiques" in desc_lower or "dégâts d'attaque" in desc_lower
    has_true = "dégâts bruts" in desc_lower

    if has_true and has_magic:
        return "Hybrid"
    if has_true:
        return "True"
    if has_magic and has_physical:
        return "Hybrid"
    if has_magic:
        return "AP"
    if has_physical:
        return "AD"
    return "None"


# --- FONCTION PRINCIPALE ---

def import_champions():
    conn = get_connection()
    cursor = conn.cursor()

    print("Recuperation de la liste des champions...")
    response = httpx.get(f"{BASE_URL}/champion.json", timeout=30)
    all_champions = response.json()["data"]
    total = len(all_champions)

    print(f"{total} champions trouves. Debut de l'import...\n")

    count = 0
    for key, champ_basic in all_champions.items():
        count += 1

        # Recupere la fiche detaillee du champion (stats + spells)
        detail_response = httpx.get(f"{BASE_URL}/champion/{key}.json", timeout=30)
        champ = detail_response.json()["data"][key]

        stats = champ["stats"]
        info = champ["info"]
        tags = champ.get("tags", [])

        # --- INSERT CHAMPION ---
        cursor.execute(
            """
            INSERT INTO champion (
                name, title, main_role, damage_type, secondary_role, attack_range,
                difficulty, description, resource_type,
                mana_base, mana_per_lvl, mana_regen_base, mana_regen_per_lvl,
                hp_base, hp_per_lvl, hp_regen_base, hp_regen_per_lvl,
                armor_base, armor_per_lvl, rm_base, rm_per_lvl,
                ad_base, ad_per_lvl,
                attackspeed_base, attackspeed_ratio, attackspeed_per_lvl,
                movespeed
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s
            )
            RETURNING id_champion
            """,
            (
                champ["name"],                              # name
                champ.get("title", ""),                     # title
                tags[0] if tags else "Fighter",             # main_role
                get_damage_type(tags, info),                # damage_type
                tags[1] if len(tags) > 1 else None,        # secondary_role
                get_attack_range(stats["attackrange"]),     # attack_range
                max(1, info.get("difficulty", 5)),            # difficulty (min 1 car la BDD exige 1-10)
                champ.get("blurb", ""),                     # description (resume court)
                get_resource_type(champ.get("partype", "")),# resource_type
                stats.get("mp", 0),                         # mana_base
                stats.get("mpperlevel", 0),                 # mana_per_lvl
                stats.get("mpregen", 0),                    # mana_regen_base
                stats.get("mpregenperlevel", 0),            # mana_regen_per_lvl
                stats["hp"],                                # hp_base
                stats["hpperlevel"],                        # hp_per_lvl
                stats["hpregen"],                           # hp_regen_base
                stats["hpregenperlevel"],                   # hp_regen_per_lvl
                stats["armor"],                             # armor_base
                stats["armorperlevel"],                     # armor_per_lvl
                stats["spellblock"],                        # rm_base (magic resist)
                stats["spellblockperlevel"],                # rm_per_lvl
                stats["attackdamage"],                      # ad_base
                stats["attackdamageperlevel"],               # ad_per_lvl
                stats["attackspeed"],                        # attackspeed_base
                stats["attackspeed"],                        # attackspeed_ratio (= base, approximation)
                stats["attackspeedperlevel"],                # attackspeed_per_lvl
                stats["movespeed"],                          # movespeed
            )
        )

        # Recupere l'id du champion qu'on vient d'inserer
        champion_id = cursor.fetchone()[0]

        # --- INSERT PASSIVE (comme un spell avec input_key = 'Passive') ---
        passive = champ["passive"]
        passive_desc = passive.get("description", "")
        is_cc, type_cc = detect_cc(passive_desc)

        cursor.execute(
            """
            INSERT INTO spell (input_key, name, description, is_cc, type_cc, damage_type, id_champion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "Passive",
                passive["name"],
                passive_desc,
                is_cc,
                type_cc,
                detect_spell_damage_type(passive_desc),
                champion_id,
            )
        )

        # --- INSERT SPELLS (Q, W, E, R) ---
        spell_keys = ["Q", "W", "E", "R"]
        resource = get_resource_type(champ.get("partype", ""))

        for i, spell in enumerate(champ["spells"]):
            spell_desc = spell.get("description", "")
            is_cc, type_cc = detect_cc(spell_desc)

            # Determine mana_cost ou energy_cost selon la ressource du champion
            cost_burn = spell.get("costBurn", "0")
            mana_cost = cost_burn if resource == "mana" else None
            energy_cost = cost_burn if resource == "energy" else None

            cursor.execute(
                """
                INSERT INTO spell (
                    input_key, name, description, mana_cost, energy_cost,
                    cooldown_base, damage_type, is_cc, type_cc, id_champion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    spell_keys[i],                          # Q, W, E ou R
                    spell["name"],
                    spell_desc,
                    mana_cost,
                    energy_cost,
                    spell.get("cooldownBurn", "0"),          # ex: "12/11/10/9/8"
                    detect_spell_damage_type(spell_desc),
                    is_cc,
                    type_cc,
                    champion_id,
                )
            )

        print(f"  [{count}/{total}] {champ['name']} OK")

        # Petite pause pour ne pas surcharger l'API Riot
        time.sleep(0.05)

    # Valide tous les inserts en BDD
    conn.commit()
    cursor.close()
    conn.close()

    print(f"\nImport termine ! {count} champions importes avec leurs spells.")


# Point d'entree : ce bloc s'execute uniquement quand on lance le script directement
# (pas quand on l'importe depuis un autre fichier)
if __name__ == "__main__":
    import_champions()
