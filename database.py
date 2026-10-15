"""Conexión asíncrona a MongoDB Atlas con Motor y ciclo de vida global (lifespan)."""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "APIMODULAR")
COLL_PRODUCTOS = os.getenv("COLL_PRODUCTOS", "PRODUCTOS")

# Se llenan al arrancar la app
client: AsyncIOMotorClient | None = None
productos = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Abre la conexión al iniciar la API y la cierra al apagarla."""
    global client, productos
    client = AsyncIOMotorClient(MONGODB_URI)
    await client.admin.command("ping")          # falla rápido si la URI está mal
    db = client[MONGODB_DB]
    productos = db[COLL_PRODUCTOS]
    await productos.create_index("sku", unique=True)   # regla: SKU único
    print(f"✅ Conectado a MongoDB Atlas -> {MONGODB_DB}.{COLL_PRODUCTOS}")
    yield
    client.close()
    print("🔌 Conexión a MongoDB cerrada")


def get_coll():
    return productos
