import os

from dotenv import load_dotenv

# Force libpq (la lib C derriere psycopg2) a utiliser UTF-8
# AVANT meme d'importer psycopg2, sinon le handshake plante sur Windows FR
os.environ["PGCLIENTENCODING"] = "utf-8"

import psycopg2

load_dotenv()

DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

def get_connection():
    connection = psycopg2.connect(
        host=DATABASE_HOST,
        port=DATABASE_PORT,
        database=DATABASE_NAME,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
        client_encoding="utf8"
    )
    return connection