from fastapi import FastAPI
from app.database import get_connection

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Bienvenue sur l'API LoL Assistant"}


@app.get("/health")
def health_check():
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
