"""
Script d'import des summoner spells depuis Data Dragon.

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


def import_summoner_spells():
    conn = get_connection()
    cursor = conn.cursor()

    print("Recuperation des summoner spells...")
    response = httpx.get(f"{BASE_URL}/summoner.json", timeout=30)
    all_spells = response.json()["data"]

    count = 0

    for key, spell in all_spells.items():
        # cooldown est une liste (ex: [300.0]), on prend le premier element
        cooldown_list = spell.get("cooldown", [0])
        cooldown = int(cooldown_list[0]) if cooldown_list else 0

        cursor.execute(
            """
            INSERT INTO summoner_spell (name, description, cooldown, effect)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            (
                spell["name"][:30],             # tronque a 30 car (limite VARCHAR)
                spell.get("description", ""),
                cooldown,
                spell.get("tooltip", ""),    # tooltip = description detaillee avec les effets
            )
        )
        count += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Import termine ! {count} summoner spells inserees.")


if __name__ == "__main__":
    import_summoner_spells()
