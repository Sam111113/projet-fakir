"""
Script d'import des items depuis Data Dragon.
Usage : depuis le dossier backend/, lancer :
    python -m scripts.import_items
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


def guess_category(tags, gold_total, item_from, item_into):
    """
    Deduit la categorie de l'item a partir de ses tags et son prix.
    Data Dragon ne donne pas directement Mythic/Legendary/etc,
    donc on utilise une heuristique basee sur les tags et le prix.
    """
    if "Boots" in tags:
        return "Boots"
    if "Trinket" in tags:
        return "Trinket"
    if "Consumable" in tags:
        return "Consumable"
    if "Lane" in tags or "Jungle" in tags:
        return "Starter"

    # Si l'item ne se construit en rien d'autre (pas de "into") et a des composants
    # → c'est un item final (Legendary)
    if not item_into and item_from:
        if gold_total >= 3000:
            return "Legendary"
        return "Epic"

    # Si l'item se construit en autre chose → c'est un composant
    if item_into:
        if gold_total >= 1000:
            return "Epic"
        return "Basic"

    # Item sans composant et sans upgrade → basique ou consommable
    if gold_total <= 500:
        return "Basic"
    return "Legendary"


def import_items():
    conn = get_connection()
    cursor = conn.cursor()

    print("Recuperation des items...")
    response = httpx.get(f"{BASE_URL}/item.json", timeout=30)
    all_items = response.json()["data"]

    # --- PHASE 1 : Inserer tous les items ---
    # On garde un mapping ddragon_id → id_item en BDD pour la phase 2 (composants)
    ddragon_to_db = {}
    count = 0

    for ddragon_id, item in all_items.items():
        # Ignore les items non achetables (wards posees, items de jungle transform, etc.)
        gold = item.get("gold", {})
        if not gold.get("purchasable", False):
            continue

        # Ne garde que les items de Summoner's Rift (map 11)
        maps = item.get("maps", {})
        if not maps.get("11", False):
            continue

        tags = item.get("tags", [])
        item_from = item.get("from", [])
        item_into = item.get("into", [])
        total_price = gold.get("total", 0)
        base_price = gold.get("base", 0)

        # stats est un dict de stats brutes fournies par l'item
        raw_stats = item.get("stats", {})
        # On le stocke en texte (JSON) dans la colonne provided_stats
        stats_str = str(raw_stats) if raw_stats else None

        category = guess_category(tags, total_price, item_from, item_into)

        cursor.execute(
            """
            INSERT INTO item (
                name, description, total_price, category, price_recipe,
                provided_stats, is_available
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id_item
            """,
            (
                item["name"],
                item.get("plaintext", ""),       # description courte et lisible
                total_price,
                category,
                base_price,                      # prix de la recette (= base price)
                stats_str,
                True,
            )
        )

        # fetchone() retourne None si ON CONFLICT a ignore le doublon
        result = cursor.fetchone()
        if result is None:
            continue
        db_id = result[0]
        ddragon_to_db[ddragon_id] = db_id
        count += 1

    print(f"{count} items inseres.")

    # --- PHASE 2 : Inserer les relations item_component ---
    # Chaque item a un champ "from" qui liste les IDs de ses composants
    comp_count = 0

    for ddragon_id, item in all_items.items():
        # L'item parent doit exister dans notre mapping
        if ddragon_id not in ddragon_to_db:
            continue

        parent_db_id = ddragon_to_db[ddragon_id]
        components = item.get("from", [])

        for comp_ddragon_id in components:
            # Le composant doit aussi exister dans notre mapping
            if comp_ddragon_id not in ddragon_to_db:
                continue

            comp_db_id = ddragon_to_db[comp_ddragon_id]

            cursor.execute(
                """
                INSERT INTO item_component (id_item_parent, id_item_component, quantity)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (parent_db_id, comp_db_id, 1)
            )
            comp_count += 1

    print(f"{comp_count} relations de composants inserees.")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\nImport items termine !")


if __name__ == "__main__":
    import_items()
