"""Flujo completo: revisar -> generar -> verificar -> exportar, y casos de error.

Los casos que necesitan el optimizador real se omiten si OR-Tools no está instalado;
los demás usan un motor simulado para probar cómo reacciona el servicio a cada estado.
"""
import shutil

import pytest
from openpyxl import load_workbook

from helpers import ejemplo, horario_voraz
from scheduler import service
from scheduler.exporter import exportar_horario
from scheduler.optimizer import ResultadoMotor, ortools_disponible
from scheduler.service import generar, revisar

necesita_ortools = pytest.mark.skipif(not ortools_disponible(), reason="requiere OR-Tools")


def _motor_falso(monkeypatch, estado, asignaciones=None, mensajes=None):
    def falso(datos, sesiones, disp=None, relajar=frozenset(), limite=None, optimizar=True):
        return ResultadoMotor(estado, asignaciones(datos, sesiones, disp) if asignaciones else [], 0.0, 0.5, mensajes or [])

    monkeypatch.setattr(service.optimizer, "resolver", falso)


@necesita_ortools
def test_flujo_completo_con_el_motor_real(tmp_path):
    rev = revisar(ejemplo("datos_validos.xlsx"))
    salida = generar(rev, limite_segundos=30)
    assert salida.exitoso and salida.estado_motor in ("OPTIMAL", "FEASIBLE")
    ruta = exportar_horario(salida, str(tmp_path / "h.xlsx"))
    assert "HORARIO_GENERAL" in load_workbook(ruta).sheetnames


@necesita_ortools
def test_infactible_del_solver_distingue_inviable_de_inconcluso():
    rev = revisar(ejemplo("datos_infactibles_solver.xlsx"))
    salida = generar(rev, limite_segundos=10)
    assert salida.estado == "SIN_SOLUCION" and salida.estado_motor == "INFEASIBLE" and salida.sugerencias


def test_entrada_invalida_no_llega_al_motor():
    rev = revisar(ejemplo("datos_infactibles.xlsx"))
    salida = generar(rev)
    assert salida.estado == "ENTRADA_INVALIDA" and not salida.exitoso and salida.asignaciones == []


def test_estado_listo_con_motor_simulado(monkeypatch):
    rev = revisar(ejemplo("datos_validos.xlsx"))
    _motor_falso(monkeypatch, "FEASIBLE", lambda d, s, dp: horario_voraz(d, s, dp))
    salida = generar(rev)
    assert salida.exitoso and "No alcanzamos a demostrar" in salida.mensaje
    assert salida.metricas["sesiones"] == 48


def test_optimo_se_comunica_como_el_mejor_posible(monkeypatch):
    rev = revisar(ejemplo("datos_validos.xlsx"))
    _motor_falso(monkeypatch, "OPTIMAL", lambda d, s, dp: horario_voraz(d, s, dp))
    assert "mejor horario posible" in generar(rev).mensaje


def test_unknown_no_se_presenta_como_imposible(monkeypatch):
    rev = revisar(ejemplo("datos_validos.xlsx"))
    _motor_falso(monkeypatch, "UNKNOWN")
    salida = generar(rev)
    assert salida.estado == "INCONCLUSO" and "NO significa que sea imposible" in salida.mensaje
    assert not salida.exitoso and salida.asignaciones == []


def test_infeasible_ofrece_pistas(monkeypatch):
    rev = revisar(ejemplo("datos_validos.xlsx"))
    _motor_falso(monkeypatch, "INFEASIBLE")
    monkeypatch.setattr(service, "diagnosticar_inviabilidad", lambda *a, **k: ["pista de ejemplo"])
    salida = generar(rev)
    assert salida.estado == "SIN_SOLUCION" and salida.sugerencias == ["pista de ejemplo"]


def test_horario_invalido_del_motor_nunca_se_presenta_como_exitoso(monkeypatch):
    rev = revisar(ejemplo("datos_validos.xlsx"))

    def con_empalme(d, s, dp):
        a = horario_voraz(d, s, dp)
        x = a[0]
        i = next(i for i, z in enumerate(a) if z.profesor_id == x.profesor_id and z.grupo != x.grupo)
        import dataclasses

        a[i] = dataclasses.replace(a[i], dia=x.dia, inicio=x.inicio)
        return a

    _motor_falso(monkeypatch, "OPTIMAL", con_empalme)
    salida = generar(rev)
    assert salida.estado == "NO_VERIFICADO" and not salida.exitoso and salida.asignaciones == []


def test_error_interno_no_expone_trazas(monkeypatch):
    rev = revisar(ejemplo("datos_validos.xlsx"))

    def revienta(*a, **k):
        raise RuntimeError("detalle técnico secreto /ruta/interna")

    monkeypatch.setattr(service.optimizer, "resolver", revienta)
    salida = generar(rev)
    assert salida.estado == "ERROR"
    assert "secreto" not in salida.mensaje and "/ruta" not in salida.mensaje


def test_repetir_la_generacion_tras_corregir_los_datos(tmp_path):
    # 1) archivo con un error  2) se corrige  3) vuelve a revisarse y queda en orden
    malo = tmp_path / "malo.xlsx"
    shutil.copy(ejemplo("datos_infactibles.xlsx"), malo)
    assert not revisar(str(malo)).ok
    assert revisar(ejemplo("datos_validos.xlsx")).ok
