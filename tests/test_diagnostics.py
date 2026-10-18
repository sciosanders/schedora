import pytest

from helpers import datos_minimos, disp_fila, ejemplo, preparar
from scheduler.diagnostics import diagnosticar_inviabilidad, verificaciones_previas
from scheduler.models import Materia, Oferta, Profesor
from scheduler.optimizer import ortools_disponible
from scheduler.service import revisar


def _previas(datos):
    sesiones, disp = preparar(datos)
    return [p.mensaje for p in verificaciones_previas(datos, sesiones, disp)]


def test_datos_holgados_no_generan_errores_previos():
    assert _previas(datos_minimos()) == []


def test_materia_sin_profesor_elegible():
    d = datos_minimos()
    d.materias.append(Materia("ESP", "Español", 1))
    d.ofertas.append(Oferta("O2", "1A", "ESP", 2))
    assert any("Nadie puede impartir «Español»" in m for m in _previas(d))


def test_profesor_inactivo_no_cuenta_como_elegible():
    d = datos_minimos()
    d.profesores[0].activo = False
    assert any("Nadie puede impartir" in m for m in _previas(d))


def test_sesion_de_2_horas_sin_franja_libre():
    d = datos_minimos()
    # hay horas libres, pero nunca 2 seguidas
    d.disponibilidad = [disp_fila("P1", "lunes", 8, 9), disp_fila("P1", "lunes", 10, 11), disp_fila("P1", "martes", 8, 9)]
    assert any("franja libre" in m for m in _previas(d))


def test_demanda_mayor_que_capacidad_de_la_materia():
    d = datos_minimos()
    d.profesores[0].horas_maximas = 2  # la oferta pide 4 h
    assert any("solo pueden ofrecer 2 h" in m for m in _previas(d))


def test_grupo_que_pide_mas_horas_que_el_calendario():
    d = datos_minimos()
    d.materias.append(Materia("ING", "Inglés", 1))
    d.profesores.append(Profesor("P2", "Luis", {"ING"}))
    d.ofertas.append(Oferta("O2", "1A", "ING", 70))  # el calendario tiene 66 h
    assert any("El grupo 1A pide" in m for m in _previas(d))


def test_minimo_imposible_de_alcanzar():
    d = datos_minimos()
    d.profesores[0].horas_minimas = 10  # las materias del profesor suman 4 h
    assert any("debe dar al menos 10 h" in m for m in _previas(d))


def test_profesor_obligatorio_con_mas_carga_de_la_posible():
    d = datos_minimos()
    d.ofertas[0].profesor_obligatorio = "P1"
    d.disponibilidad = [disp_fila("P1", "lunes", 8, 10)]
    assert any("marcado como obligatorio" in m for m in _previas(d))


def test_ejemplo_infactible_previo_se_detecta_sin_solver():
    rev = revisar(ejemplo("datos_infactibles.xlsx"))
    assert not rev.ok and any("Educación Física" in p.mensaje for p in rev.errores)


@pytest.mark.skipif(not ortools_disponible(), reason="requiere OR-Tools")
def test_diagnostico_tras_infactible_sugiere_relajar_disponibilidad():
    rev = revisar(ejemplo("datos_infactibles_solver.xlsx"))
    assert rev.ok  # las verificaciones previas no lo detectan
    pistas = " ".join(diagnosticar_inviabilidad(rev.datos, rev.sesiones, rev.disp, segundos_por_prueba=5))
    assert "disponibilidad de los profesores" in pistas
    assert "no identifican una causa única" in pistas
