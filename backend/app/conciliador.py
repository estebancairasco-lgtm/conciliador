"""Reglas de negocio del conciliador de facturas y retenciones.

Este módulo no depende de FastAPI: recibe los CSV como bytes y devuelve
diccionarios. Así las reglas se pueden probar y leer sin levantar el servidor.
"""
from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

COLUMNAS_FACTURAS = (
    "id_factura", "nit_proveedor", "fecha_factura", "concepto",
    "base_gravable", "tarifa_iva", "valor_iva",
    "tarifa_retencion", "valor_retencion", "total_factura",
)
COLUMNAS_CONTABILIDAD = (
    "id_factura", "fecha_contabilizacion", "cuenta_contable",
    "centro_costo", "valor_debito", "valor_credito", "estado",
)
CAMPOS_NUMERICOS = (
    "base_gravable", "tarifa_iva", "valor_iva",
    "tarifa_retencion", "valor_retencion", "total_factura",
)

# Diferencia máxima aceptada (en pesos) para considerar que dos valores coinciden.
TOLERANCIA = Decimal("1")
ESTADO_CONTABILIZADA = "contabilizada"

CAUSAS = {
    "CAMPO_VACIO": "Campos obligatorios vacíos en la factura",
    "DATO_INVALIDO": "Valores no numéricos en campos numéricos",
    "IVA_INCORRECTO": "El IVA declarado no es base gravable × tarifa de IVA",
    "RETENCION_INCORRECTA": "La retención declarada no es base gravable × tarifa de retención",
    "TOTAL_INCORRECTO": "El total no es base + IVA esperado − retención",
    "DUPLICADA": "El id de factura está repetido en facturas.csv",
    "SIN_CONTABILIZAR": "La factura no tiene registro en contabilidad.csv",
    "ESTADO_NO_CONTABILIZADO": "El registro contable no está en estado Contabilizada",
    "ASIENTO_DESCUADRADO": "La suma de débitos no es igual a la suma de créditos",
    "DIFERENCIA_VALOR_CONTABLE": "El valor contabilizado no coincide con el total de la factura",
}


class ArchivoInvalido(ValueError):
    """El archivo no se puede procesar (vacío, sin columnas obligatorias, etc.)."""


# --------------------------------------------------------------------------
# Lectura de archivos
# --------------------------------------------------------------------------
def leer_csv(contenido: bytes, nombre: str, columnas: tuple[str, ...]) -> list[dict[str, str]]:
    """Lee un CSV, valida las columnas obligatorias y devuelve filas con texto limpio.

    Cada fila trae además la clave '_fila' con su número de línea en el archivo.
    """
    if not contenido.strip():
        raise ArchivoInvalido(f"El archivo '{nombre}' está vacío.")
    try:
        texto = contenido.decode("utf-8-sig")  # utf-8-sig elimina el BOM de Excel
    except UnicodeDecodeError:
        texto = contenido.decode("latin-1")

    primera = texto.splitlines()[0]
    delimitador = ";" if primera.count(";") > primera.count(",") else ","
    lector = csv.DictReader(io.StringIO(texto), delimiter=delimitador)

    encabezados = [(h or "").strip().lower() for h in (lector.fieldnames or [])]
    faltantes = [c for c in columnas if c not in encabezados]
    if faltantes:
        raise ArchivoInvalido(
            f"Al archivo '{nombre}' le faltan columnas obligatorias: {', '.join(faltantes)}."
        )
    lector.fieldnames = encabezados

    filas: list[dict[str, str]] = []
    for fila in lector:
        limpia = {k: (v or "").strip() for k, v in fila.items() if k}
        if not any(limpia.values()):
            continue  # línea en blanco
        limpia["_fila"] = str(lector.line_num)
        filas.append(limpia)
    if not filas:
        raise ArchivoInvalido(f"El archivo '{nombre}' no tiene registros.")
    return filas


def _decimal(valor: str) -> Decimal:
    numero = Decimal(valor)
    if not numero.is_finite():
        raise InvalidOperation(valor)
    return numero


def _redondear(valor: Decimal) -> Decimal:
    """Redondea al peso (COP no maneja centavos en estos documentos)."""
    return valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _num(valor: Decimal | None) -> int | float | None:
    if valor is None:
        return None
    return int(valor) if valor == valor.to_integral_value() else float(valor)


def _cop(valor: Decimal) -> str:
    return "$" + f"{int(valor):,}".replace(",", ".")


# --------------------------------------------------------------------------
# Preparación de la contabilidad
# --------------------------------------------------------------------------
def _agrupar_asientos(contabilidad: list[dict[str, str]]) -> dict[str, list[dict[str, Any]]]:
    asientos: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fila in contabilidad:
        id_factura = fila["id_factura"]
        if not id_factura:
            continue
        try:
            debito = _decimal(fila["valor_debito"])
            credito = _decimal(fila["valor_credito"])
        except InvalidOperation:
            raise ArchivoInvalido(
                f"contabilidad.csv, fila {fila['_fila']}: valor_debito y valor_credito "
                "deben ser numéricos."
            ) from None
        asientos[id_factura].append(
            {"debito": debito, "credito": credito, "estado": fila["estado"]}
        )
    return asientos


# --------------------------------------------------------------------------
# Evaluación de una factura
# --------------------------------------------------------------------------
def _evaluar_factura(
    f: dict[str, str],
    filas_por_id: dict[str, list[str]],
    asientos: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    causas: list[dict[str, str]] = []
    advertencias: list[str] = []

    def marcar(codigo: str, detalle: str) -> None:
        causas.append({"codigo": codigo, "descripcion": CAUSAS[codigo], "detalle": detalle})

    id_factura = f["id_factura"]

    # 1. Campos vacíos y numéricos inválidos
    vacios = [c for c in COLUMNAS_FACTURAS if not f.get(c)]
    if vacios:
        marcar("CAMPO_VACIO", "Vacíos: " + ", ".join(vacios))

    v: dict[str, Decimal] = {}
    invalidos = []
    for campo in CAMPOS_NUMERICOS:
        if f.get(campo):
            try:
                v[campo] = _decimal(f[campo])
            except InvalidOperation:
                invalidos.append(campo)
    if invalidos:
        marcar("DATO_INVALIDO", "No numéricos: " + ", ".join(invalidos))

    # 2. Regla 1: IVA esperado = base × tarifa IVA
    iva_esperado = ret_esperada = total_esperado = None
    if "base_gravable" in v and "tarifa_iva" in v:
        iva_esperado = _redondear(v["base_gravable"] * v["tarifa_iva"])
        if "valor_iva" in v and abs(v["valor_iva"] - iva_esperado) > TOLERANCIA:
            marcar(
                "IVA_INCORRECTO",
                f"Declarado {_cop(v['valor_iva'])}, esperado {_cop(iva_esperado)}",
            )

    # Retención esperada = base × tarifa de retención (control adicional)
    if "base_gravable" in v and "tarifa_retencion" in v:
        ret_esperada = _redondear(v["base_gravable"] * v["tarifa_retencion"])
        if "valor_retencion" in v and abs(v["valor_retencion"] - ret_esperada) > TOLERANCIA:
            marcar(
                "RETENCION_INCORRECTA",
                f"Declarada {_cop(v['valor_retencion'])}, esperada {_cop(ret_esperada)}",
            )

    # 3. Regla 2: total = base + IVA esperado − retención declarada
    #    Se usa el IVA *esperado* para que un error de IVA no arrastre un
    #    falso error de total: cada causa se reporta por separado.
    if iva_esperado is not None and "valor_retencion" in v and "total_factura" in v:
        total_esperado = v["base_gravable"] + iva_esperado - v["valor_retencion"]
        if abs(v["total_factura"] - total_esperado) > TOLERANCIA:
            marcar(
                "TOTAL_INCORRECTO",
                f"Declarado {_cop(v['total_factura'])}, esperado {_cop(total_esperado)}",
            )

    # 4. Regla 3a: duplicados
    es_duplicada = bool(id_factura) and len(filas_por_id[id_factura]) > 1
    if es_duplicada:
        filas = filas_por_id[id_factura]
        marcar("DUPLICADA", f"Aparece {len(filas)} veces (filas {', '.join(filas)})")

    # 5. Regla 3b y cruce contable
    estado_contable = None
    valor_contabilizado = None
    if id_factura:
        entradas = asientos.get(id_factura, [])
        if not entradas:
            marcar("SIN_CONTABILIZAR", "No existe registro en contabilidad.csv")
        else:
            estados = sorted({e["estado"] or "(vacío)" for e in entradas})
            estado_contable = ", ".join(estados)
            if any(e["estado"].lower() != ESTADO_CONTABILIZADA for e in entradas):
                marcar("ESTADO_NO_CONTABILIZADO", f"Estado en contabilidad: {estado_contable}")

            debitos = sum((e["debito"] for e in entradas), Decimal(0))
            creditos = sum((e["credito"] for e in entradas), Decimal(0))
            valor_contabilizado = debitos
            if abs(debitos - creditos) > TOLERANCIA:
                marcar(
                    "ASIENTO_DESCUADRADO",
                    f"Débitos {_cop(debitos)} vs créditos {_cop(creditos)}",
                )
            elif not es_duplicada and "total_factura" in v and abs(debitos - v["total_factura"]) > TOLERANCIA:
                # En duplicadas no se compara: no se sabe a cuál factura corresponde el asiento.
                marcar(
                    "DIFERENCIA_VALOR_CONTABLE",
                    f"Contabilizado {_cop(debitos)}, factura {_cop(v['total_factura'])}",
                )

            en_cero = [e for e in entradas if e["debito"] == 0 and e["credito"] == 0]
            if en_cero:
                advertencias.append(
                    f"{len(en_cero)} línea(s) contable(s) con débito y crédito en cero"
                )

    return {
        "fila": int(f["_fila"]),
        "id_factura": id_factura,
        "nit_proveedor": f["nit_proveedor"],
        "fecha_factura": f["fecha_factura"],
        "concepto": f["concepto"],
        "base_gravable": _num(v.get("base_gravable")),
        "tarifa_iva": _num(v.get("tarifa_iva")),
        "valor_iva": _num(v.get("valor_iva")),
        "iva_esperado": _num(iva_esperado),
        "tarifa_retencion": _num(v.get("tarifa_retencion")),
        "valor_retencion": _num(v.get("valor_retencion")),
        "retencion_esperada": _num(ret_esperada),
        "total_factura": _num(v.get("total_factura")),
        "total_esperado": _num(total_esperado),
        "estado_contable": estado_contable,
        "valor_contabilizado": _num(valor_contabilizado),
        "estado": "Con inconsistencia" if causas else "Correcta",
        "causas": causas,
        "advertencias": advertencias,
    }


# --------------------------------------------------------------------------
# Punto de entrada
# --------------------------------------------------------------------------
def conciliar(
    facturas: list[dict[str, str]], contabilidad: list[dict[str, str]]
) -> dict[str, Any]:
    """Aplica todas las reglas y devuelve {'resumen': ..., 'detalle': [...]}."""
    asientos = _agrupar_asientos(contabilidad)

    filas_por_id: dict[str, list[str]] = defaultdict(list)
    for f in facturas:
        if f["id_factura"]:
            filas_por_id[f["id_factura"]].append(f["_fila"])

    detalle = [_evaluar_factura(f, filas_por_id, asientos) for f in facturas]

    conteo = Counter(c["codigo"] for d in detalle for c in d["causas"])
    con_inconsistencia = sum(1 for d in detalle if d["estado"] == "Con inconsistencia")
    ids_facturas = set(filas_por_id)

    resumen = {
        "total_facturas": len(detalle),
        "correctas": len(detalle) - con_inconsistencia,
        "con_inconsistencia": con_inconsistencia,
        "porcentaje_inconsistencias": round(100 * con_inconsistencia / len(detalle), 1),
        "con_advertencias": sum(1 for d in detalle if d["advertencias"]),
        "total_registros_contables": len(contabilidad),
        "causas": [
            {"codigo": c, "descripcion": desc, "cantidad": conteo.get(c, 0)}
            for c, desc in CAUSAS.items()
        ],
        "ids_contables_sin_factura": sorted(set(asientos) - ids_facturas),
    }
    return {"resumen": resumen, "detalle": detalle}


def procesar_archivos(facturas_csv: bytes, contabilidad_csv: bytes) -> dict[str, Any]:
    facturas = leer_csv(facturas_csv, "facturas.csv", COLUMNAS_FACTURAS)
    contabilidad = leer_csv(contabilidad_csv, "contabilidad.csv", COLUMNAS_CONTABILIDAD)
    return conciliar(facturas, contabilidad)
