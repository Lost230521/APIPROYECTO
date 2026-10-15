"""Proyecto modular I — API concurrente con base de datos.
Gestor de Inventario: FastAPI + Pydantic + MongoDB Atlas (Motor) + asyncio.to_thread.
Ejecutar:  py -m uvicorn main:app --reload --port 8010
"""
import asyncio
import math
import time
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from database import get_coll, lifespan

app = FastAPI(title="API Inventario Concurrente", version="1.0", lifespan=lifespan)


# ---------------------------- Modelos Pydantic ----------------------------
class ProductoIn(BaseModel):
    sku: str = Field(..., min_length=3, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    nombre: str = Field(..., min_length=2, max_length=80)
    categoria: str = Field(..., min_length=2, max_length=40)
    precio: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    ventas_diarias: float = Field(1, ge=0, description="Promedio de unidades vendidas por día")


class ProductoUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=80)
    categoria: str | None = Field(None, min_length=2, max_length=40)
    precio: float | None = Field(None, gt=0)
    stock: int | None = Field(None, ge=0)
    ventas_diarias: float | None = Field(None, ge=0)


class ProductoOut(ProductoIn):
    id: str


def a_salida(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


def oid(id_: str) -> ObjectId:
    try:
        return ObjectId(id_)
    except (InvalidId, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ID inválido")


# ------------------------------- Rutas CRUD -------------------------------
@app.get("/", include_in_schema=False)
async def inicio():
    return RedirectResponse("/app/")


@app.get("/productos", response_model=list[ProductoOut])
async def listar_productos():
    return [a_salida(d) async for d in get_coll().find().sort("nombre", 1)]


@app.get("/productos/{id}", response_model=ProductoOut)
async def obtener_producto(id: str):
    doc = await get_coll().find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return a_salida(doc)


@app.post("/productos", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
async def crear_producto(producto: ProductoIn):
    data = producto.model_dump()
    data["sku"] = data["sku"].upper()
    try:
        res = await get_coll().insert_one(data)
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Ya existe un producto con SKU {data['sku']}")
    data["_id"] = res.inserted_id
    return a_salida(data)


@app.put("/productos/{id}", response_model=ProductoOut)
async def actualizar_producto(id: str, cambios: ProductoUpdate):
    data = cambios.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No se enviaron campos para actualizar")
    doc = await get_coll().find_one_and_update(
        {"_id": oid(id)}, {"$set": data}, return_document=ReturnDocument.AFTER
    )
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return a_salida(doc)


@app.delete("/productos/{id}")
async def eliminar_producto(id: str):
    res = await get_coll().delete_one({"_id": oid(id)})
    if res.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return {"mensaje": "Producto eliminado", "id": id}


# ------------------- Concurrencia: tarea intensiva de CPU -------------------
def calcular_proyeccion(productos: list[dict], dias: int) -> dict:
    """Tarea BLOQUEANTE (CPU). Simula una simulación pesada de stock día por día."""
    inicio = time.perf_counter()
    resultado = []
    for p in productos:
        stock = float(p["stock"])
        venta = float(p.get("ventas_diarias", 1))
        dia_agotado = None
        for dia in range(1, dias + 1):
            # cálculo pesado simulado (Monte Carlo determinista)
            factor = sum(math.sin(dia * k) ** 2 for k in range(1, 20000)) / 20000
            stock -= venta * (0.5 + factor)
            if stock <= 0 and dia_agotado is None:
                dia_agotado = dia
        resultado.append({
            "sku": p["sku"],
            "nombre": p["nombre"],
            "stock_actual": p["stock"],
            "stock_proyectado": max(round(stock, 1), 0),
            "dia_agotado": dia_agotado,
            "reabastecer": dia_agotado is not None,
        })
    time.sleep(1)  # bloqueo simulado extra (p.ej. generar un PDF)
    return {
        "dias": dias,
        "productos": resultado,
        "en_riesgo": sum(r["reabastecer"] for r in resultado),
        "segundos": round(time.perf_counter() - inicio, 2),
    }


@app.get("/reportes/proyeccion-stock")
async def proyeccion_stock(dias: int = 30):
    if not 1 <= dias <= 365:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "dias debe estar entre 1 y 365")
    productos = [d async for d in get_coll().find({}, {"_id": 0})]
    # Se delega a un hilo secundario para NO bloquear el event loop
    return await asyncio.to_thread(calcular_proyeccion, productos, dias)


@app.get("/ping")
async def ping():
    """Sirve para comprobar que el servidor responde mientras corre el reporte."""
    return {"ok": True, "hora": time.strftime("%H:%M:%S")}


# ------------------------------- Frontend -------------------------------
app.mount("/app", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")


if __name__ == "__main__":
    # Permite correrlo con el botón Run de PyCharm
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8010)
