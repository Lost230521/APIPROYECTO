# Proyecto modular I — API concurrente con base de datos

Gestor de inventario con **FastAPI + Pydantic**, **MongoDB Atlas** (driver asíncrono Motor),
concurrencia con **asyncio.to_thread()** y frontend **HTML5 + JS vanilla** servido con StaticFiles.

## Estructura
```
API/
├── .env              credenciales (no se sube)
├── database.py       conexión Motor + lifespan (@asynccontextmanager)
├── main.py           modelos Pydantic, CRUD, endpoint concurrente, StaticFiles
├── requirements.txt
└── static/index.html interfaz con fetch()
```

## Ejecutar
```
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
py -m uvicorn main:app --reload --port 8010
```
- Interfaz: http://127.0.0.1:8010/app/
- Documentación: http://127.0.0.1:8010/docs

## Endpoints
| Método | Ruta | Descripción | Códigos |
|---|---|---|---|
| GET | /productos | Lista productos | 200 |
| GET | /productos/{id} | Un producto | 200, 400, 404 |
| POST | /productos | Crea (SKU único) | 201, 400, 422 |
| PUT | /productos/{id} | Actualiza parcial | 200, 400, 404, 422 |
| DELETE | /productos/{id} | Elimina | 200, 400, 404 |
| GET | /reportes/proyeccion-stock?dias=30 | Proyección pesada en hilo secundario | 200, 400 |
| GET | /ping | Comprueba que el servidor no se bloquea | 200 |

## Concurrencia
`calcular_proyeccion()` es una función síncrona y pesada (cálculo por día + `time.sleep`).
El endpoint la ejecuta con `await asyncio.to_thread(...)`, así el event loop sigue atendiendo
otras peticiones. La interfaz lo demuestra: mientras calcula, hace `fetch('/ping')` cada 300 ms
y el contador sigue avanzando.
