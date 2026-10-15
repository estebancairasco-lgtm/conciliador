"""API REST del conciliador de facturas y retenciones."""
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .conciliador import ArchivoInvalido, procesar_archivos

TAMANO_MAXIMO = 5 * 1024 * 1024  # 5 MB por archivo

app = FastAPI(
    title="Conciliador de facturas y retenciones",
    description="Cruza facturas de proveedores contra los registros contabilizados.",
    version="1.0.0",
)

# El frontend Angular corre en el puerto 4200 durante el desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _leer(archivo: UploadFile) -> bytes:
    contenido = await archivo.read(TAMANO_MAXIMO + 1)
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(413, f"'{archivo.filename}' supera el tamaño máximo de 5 MB.")
    if archivo.filename and not archivo.filename.lower().endswith(".csv"):
        raise HTTPException(422, f"'{archivo.filename}' no es un archivo .csv.")
    return contenido


@app.get("/api/salud")
def salud() -> dict[str, str]:
    return {"estado": "ok"}


@app.post("/api/conciliar")
async def conciliar_archivos(
    facturas: UploadFile = File(..., description="facturas.csv"),
    contabilidad: UploadFile = File(..., description="contabilidad.csv"),
) -> dict:
    """Recibe los dos CSV y devuelve el resumen y el detalle por factura."""
    facturas_bytes = await _leer(facturas)
    contabilidad_bytes = await _leer(contabilidad)
    try:
        return procesar_archivos(facturas_bytes, contabilidad_bytes)
    except ArchivoInvalido as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
