from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "port": os.environ.get("PORT", "unknown"),
        "db_url": os.environ.get("DATABASE_URL", "not_set")
    }
