"""
Script d'import des runes depuis Data Dragon.
Usage : depuis le dossier backend/, lancer :
    python -m scripts.import_runes
"""

import sys
import os
import certifi

# Fix Windows : force le bon chemin vers les certificats SSL
os.environ["SSL_CERT_FILE"] = certifi.where()

import httpx

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import get_connection

DDRAGON_VERSION = "16.3.1"
BASE_URL = f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/data/fr_FR"

# Mapping index du slot → rune_rank dans ta BDD
SLOT_TO_RANK = {
    0: "Keystone",
    1: "Slot1",
    2: "Slot2",
    3: "Slot3",
}

# Mapping noms francais → anglais (la BDD attend les noms en anglais)
TREE_NAME_MAP = {
    "Précision": "Precision",
    "Domination": "Domination",
    "Sorcellerie": "Sorcery",
    "Volonté": "Resolve",
    "Inspiration": "Inspiration",
}


def import_runes():
    conn = get_connection()
    cursor = conn.cursor()

    print("Recuperation des runes...")
    response = httpx.get(f"{BASE_URL}/runesReforged.json", timeout=30)
    rune_trees = response.json()

    count = 0

    # Chaque element est un arbre de runes (Precision, Domination, etc.)
    for tree in rune_trees:
        tree_name_fr = tree["name"]
        tree_name = TREE_NAME_MAP.get(tree_name_fr, tree_name_fr)

        # Chaque arbre a 4 slots (Keystone + Slot1 + Slot2 + Slot3)
        for slot_index, slot in enumerate(tree["slots"]):
            rune_rank = SLOT_TO_RANK[slot_index]

            # Chaque slot contient une liste de runes
            for rune in slot["runes"]:
                cursor.execute(
                    """
                    INSERT INTO rune (name, description, rune_tree, rune_rank)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    (
                        rune["name"],
                        rune.get("shortDesc", ""),
                        tree_name,
                        rune_rank,
                    )
                )
                count += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Import termine ! {count} runes inserees.")


if __name__ == "__main__":
    import_runes()
