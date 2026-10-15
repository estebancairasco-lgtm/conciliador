# Conciliador de facturas y retenciones

Prototipo web que cruza el archivo de **facturas de proveedores** contra el archivo de **registros contabilizados**, aplica reglas básicas de validación contable y tributaria, y presenta un resumen y un detalle de las facturas correctas y de las que tienen inconsistencias.

- **Backend:** Python + FastAPI (API REST)
- **Frontend:** Angular 21
- **Datos de prueba:** `datos_prueba/` (ficticios)

## Contenido del repositorio

```
conciliador/
├── backend/          API REST en FastAPI (reglas de negocio, pruebas)
├── frontend/         Aplicación Angular
├── datos_prueba/     facturas.csv y contabilidad.csv de ejemplo
└── README.md
```

Cada carpeta (`backend/README.md`, `frontend/README.md`) tiene además su propio detalle.

## Versiones y requisitos

| Herramienta | Versión |
|---|---|
| Python | 3.10 a 3.13 (probado con 3.12) |
| Node.js | 20.19+, 22.12+ o 24+ (probado con 24) |
| npm | 10 o superior (probado con 11) |
| FastAPI / Uvicorn | 0.115.6 / 0.34.0 |
| Angular / TypeScript | 21.2 / 5.9 |

Las dependencias exactas están en `backend/requirements.txt` y `frontend/package-lock.json`. Todo es software libre y no requiere acceso a sistemas corporativos ni credenciales.

> **No uses Python 3.14 o superior:** algunas dependencias aún no publican paquetes precompilados y `pip` intenta compilarlas (en Windows exige herramientas de C++). Verifica con `python --version`.

## Instalación y ejecución

Se necesitan **dos terminales**: una para el backend y otra para el frontend. Inicia primero el backend.

### Windows (PowerShell)

**Terminal 1 – Backend**
```powershell
cd backend
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
Debe aparecer `Uvicorn running on http://127.0.0.1:8000`. Deja esta terminal abierta.

**Terminal 2 – Frontend**
```powershell
cd frontend
Set-ExecutionPolicy -Scope Process Bypass
npm install
npm start
```
Cuando compile, abre **http://localhost:4200**.

### Linux / macOS

**Terminal 1 – Backend**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 – Frontend**
```bash
cd frontend
npm install
npm start
```
Abre **http://localhost:4200**.

## Cómo usar la aplicación

1. Selecciona `facturas.csv` y `contabilidad.csv` (están en `datos_prueba/`).
2. Pulsa **Procesar**.
3. Revisa el **resumen** (total de facturas, correctas, con inconsistencia y causas) y el **detalle** por factura.
4. Filtra la tabla por estado (Todos / Correcta / Con inconsistencia) o busca por id de factura.

### Resultado esperado con los archivos de ejemplo

| Indicador | Valor |
|---|---|
| Total de facturas (filas) | 50 |
| Correctas | 32 |
| Con inconsistencia | 18 (36 %) |

| Causa | Filas | Facturas |
|---|---|---|
| IVA incorrecto | 2 | FAC-0006, FAC-0018 |
| Total incorrecto | 3 | FAC-0009, FAC-0023, FAC-0036 |
| Duplicada | 4 | FAC-0004, FAC-0015 (2 filas cada una) |
| Sin registro contable | 4 | FAC-0007, FAC-0021, FAC-0034, FAC-0042 |
| Registro en estado Pendiente | 3 | FAC-0011, FAC-0027, FAC-0039 |
| Campos vacíos | 3 | FAC-0013, FAC-0029, FAC-0042 |

FAC-0042 tiene dos causas (campo vacío y sin contabilizar), por eso la suma de causas (19) supera las 18 facturas con inconsistencia. Además, 7 filas (FAC-0001 a FAC-0006, con FAC-0004 repetida) muestran una **advertencia** por líneas contables en cero, que no cambia su estado.

## Pruebas automáticas (backend)

Con el entorno virtual activo, desde `backend/`:
```bash
python -m pytest -q
```
Resultado esperado: `6 passed`. Las pruebas validan las reglas contra los archivos de ejemplo y el manejo de errores de la API.

## API

- `GET /api/salud` → `{"estado": "ok"}`
- `POST /api/conciliar` (`multipart/form-data` con los campos `facturas` y `contabilidad`) → `{ "resumen": {...}, "detalle": [...] }`
- Documentación interactiva: http://localhost:8000/docs

Errores: respuesta HTTP 422 con un mensaje legible en `detail` (archivo vacío, columnas obligatorias faltantes, archivo que no es `.csv`, valores no numéricos en contabilidad) y 413 si un archivo supera 5 MB.

## Reglas de negocio implementadas

| Código | Regla |
|---|---|
| `IVA_INCORRECTO` | `valor_iva` ≠ `base_gravable` × `tarifa_iva` |
| `TOTAL_INCORRECTO` | `total_factura` ≠ `base_gravable` + IVA esperado − `valor_retencion` |
| `RETENCION_INCORRECTA` | `valor_retencion` ≠ `base_gravable` × `tarifa_retencion` |
| `DUPLICADA` | el `id_factura` aparece más de una vez en facturas.csv |
| `SIN_CONTABILIZAR` | el `id_factura` no tiene registro en contabilidad.csv |
| `ESTADO_NO_CONTABILIZADO` | algún registro contable con estado distinto de `Contabilizada` |
| `ASIENTO_DESCUADRADO` | suma de débitos ≠ suma de créditos |
| `DIFERENCIA_VALOR_CONTABLE` | suma de débitos ≠ `total_factura` |
| `CAMPO_VACIO` / `DATO_INVALIDO` | campos obligatorios vacíos o numéricos inválidos |

Cada factura se clasifica como **Correcta** o **Con inconsistencia**, con la lista de causas y el detalle (valor declarado frente al esperado). Una factura puede tener varias causas.

## Supuestos y decisiones técnicas

- Los valores están en pesos colombianos. Los cálculos se redondean al peso y se acepta una **tolerancia de $1**.
- El total se valida con el **IVA esperado** (no con el declarado), para que un error de IVA no genere además un falso error de total; cada causa se reporta por separado.
- La retención declarada se toma tal cual para validar el total. Aparte se verifica que sea base × tarifa de retención.
- En ids **duplicados** no se compara el valor contable, porque no se sabe a cuál de las facturas corresponde el asiento. Ambas filas se marcan como inconsistentes.
- Una factura con varias líneas contables se valida con la **suma** de débitos y créditos.
- Las líneas contables con débito y crédito en cero se muestran como **advertencia** y no cambian el estado. Si el negocio las considera un error, es un cambio pequeño en `backend/app/conciliador.py`.
- "Total de facturas" cuenta **filas** de facturas.csv; un id duplicado cuenta dos veces.
- Se acepta CSV en UTF-8 (con o sin BOM) o Latin-1, separado por coma o punto y coma.
- Los registros contables sin factura se listan en el resumen, pero no se consideran inconsistencia.
- Un valor no numérico en contabilidad.csv detiene el proceso con error 422; en facturas.csv solo marca esa fila como `DATO_INVALIDO`.
- El backend no guarda datos: cada procesamiento es independiente.

## Funcionalidades no incluidas

- Autenticación, base de datos e historial de procesamientos.
- Exportar los resultados (Excel o CSV).
- Paginación de la tabla (pensada para archivos de decenas de registros).
- Pruebas automáticas del frontend (el flujo se verificó manualmente).
- Validación de formato de fechas y de NIT, y comparación entre fecha de factura y fecha de contabilización.
- Configuración por variables de entorno: la URL del backend está en `frontend/src/app/config.ts` y el CORS acepta solo `http://localhost:4200`.

## Solución de problemas

- **`la ejecución de scripts está deshabilitada`** (PowerShell): ejecuta `Set-ExecutionPolicy -Scope Process Bypass` en esa terminal y repite el comando.
- **Error de instalación con `pyyaml` o `pydantic-core`:** estás usando una versión de Python demasiado nueva. Instala Python 3.12 y crea el entorno con `py -3.12 -m venv .venv`.
- **La pantalla dice que no se pudo conectar con el backend:** verifica que la terminal 1 siga corriendo y que http://localhost:8000/docs abra.
- **El puerto 8000 o 4200 está ocupado:** cierra el programa que lo usa o cambia el puerto (y `API_URL` en `frontend/src/app/config.ts` si cambias el del backend).

## Uso de inteligencia artificial generativa

Ver `DECLARACION_IA.md`.
