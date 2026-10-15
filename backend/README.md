# Backend – Conciliador de facturas y retenciones

Python 3.10+ · FastAPI

## Ejecutar
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Documentación interactiva: http://localhost:8000/docs

## Probar
```bash
python -m pytest -q
curl -F facturas=@../datos_prueba/facturas.csv -F contabilidad=@../datos_prueba/contabilidad.csv http://localhost:8000/api/conciliar
```

## Endpoints
- `GET /api/salud`
- `POST /api/conciliar` (multipart: `facturas`, `contabilidad`) → `{ resumen, detalle[] }`. Errores de archivo: HTTP 422 con `detail` legible.

## Reglas
| Código | Regla |
|---|---|
| IVA_INCORRECTO | `valor_iva` ≠ base × tarifa_iva |
| TOTAL_INCORRECTO | `total_factura` ≠ base + IVA esperado − retención |
| RETENCION_INCORRECTA | `valor_retencion` ≠ base × tarifa_retencion |
| DUPLICADA | `id_factura` repetido en facturas.csv |
| SIN_CONTABILIZAR | id sin registro en contabilidad.csv |
| ESTADO_NO_CONTABILIZADO | algún registro con estado distinto de Contabilizada |
| ASIENTO_DESCUADRADO / DIFERENCIA_VALOR_CONTABLE | débitos ≠ créditos, o débitos ≠ total de la factura |
| CAMPO_VACIO / DATO_INVALIDO | campos obligatorios vacíos o no numéricos |

## Supuestos
- Valores en pesos, redondeados al peso; tolerancia de $1.
- El total se valida con el IVA *esperado*, para que un error de IVA no genere además un falso error de total.
- En ids duplicados no se compara el valor contable (no se sabe a qué factura pertenece el asiento).
- Líneas contables con débito y crédito en 0 se reportan como **advertencia**, sin cambiar el estado.
- Un valor no numérico en contabilidad.csv detiene el proceso con error 422; en facturas.csv solo marca esa fila.
