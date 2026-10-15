from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.conciliador import ArchivoInvalido, procesar_archivos
from app.main import app

DATOS = Path(__file__).resolve().parents[2] / "datos_prueba"
FACTURAS = (DATOS / "facturas.csv").read_bytes()
CONTABILIDAD = (DATOS / "contabilidad.csv").read_bytes()


def causas_por_id(resultado):
    salida = {}
    for d in resultado["detalle"]:
        salida.setdefault(d["id_factura"], []).extend(c["codigo"] for c in d["causas"])
    return salida


def test_resumen_archivos_de_ejemplo():
    r = procesar_archivos(FACTURAS, CONTABILIDAD)["resumen"]
    assert r["total_facturas"] == 50
    assert r["con_inconsistencia"] == 18
    assert r["correctas"] == 32


def test_causas_esperadas():
    c = causas_por_id(procesar_archivos(FACTURAS, CONTABILIDAD))
    assert c["FAC-0006"] == ["IVA_INCORRECTO"]
    assert c["FAC-0018"] == ["IVA_INCORRECTO"]
    for fid in ("FAC-0009", "FAC-0023", "FAC-0036"):
        assert c[fid] == ["TOTAL_INCORRECTO"]
    assert c["FAC-0004"].count("DUPLICADA") == 2
    assert c["FAC-0015"].count("DUPLICADA") == 2
    for fid in ("FAC-0007", "FAC-0021", "FAC-0034"):
        assert c[fid] == ["SIN_CONTABILIZAR"]
    for fid in ("FAC-0011", "FAC-0027", "FAC-0039"):
        assert c[fid] == ["ESTADO_NO_CONTABILIZADO"]
    assert c["FAC-0013"] == ["CAMPO_VACIO"]
    assert set(c["FAC-0042"]) == {"CAMPO_VACIO", "SIN_CONTABILIZAR"}
    assert c["FAC-0001"] == []  # correcta aunque tenga línea contable en cero


def test_lineas_en_cero_son_advertencia():
    r = procesar_archivos(FACTURAS, CONTABILIDAD)
    ids = {d["id_factura"] for d in r["detalle"] if d["advertencias"]}
    assert ids == {f"FAC-000{i}" for i in range(1, 7)}  # FAC-0004 sale en 2 filas por estar duplicada


def test_columna_faltante():
    malo = b"id_factura,nit_proveedor\nFAC-1,900\n"
    with pytest.raises(ArchivoInvalido, match="faltan columnas"):
        procesar_archivos(malo, CONTABILIDAD)


def test_archivo_vacio():
    with pytest.raises(ArchivoInvalido, match="vacío"):
        procesar_archivos(b"", CONTABILIDAD)


def test_api_ok_y_errores():
    cliente = TestClient(app)
    ok = cliente.post(
        "/api/conciliar",
        files={"facturas": ("facturas.csv", FACTURAS), "contabilidad": ("contabilidad.csv", CONTABILIDAD)},
    )
    assert ok.status_code == 200 and ok.json()["resumen"]["total_facturas"] == 50

    malo = cliente.post(
        "/api/conciliar",
        files={"facturas": ("facturas.csv", b"x,y\n1,2\n"), "contabilidad": ("contabilidad.csv", CONTABILIDAD)},
    )
    assert malo.status_code == 422 and "faltan columnas" in malo.json()["detail"]

    no_csv = cliente.post(
        "/api/conciliar",
        files={"facturas": ("facturas.txt", FACTURAS), "contabilidad": ("contabilidad.csv", CONTABILIDAD)},
    )
    assert no_csv.status_code == 422
