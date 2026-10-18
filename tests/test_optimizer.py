"""Pruebas del motor CP-SAT. Requieren OR-Tools (pip install -r requirements.txt)."""
import pytest

from helpers import datos_minimos, disp_fila, ejemplo, preparar
from scheduler.metrics import calcular_metricas
from scheduler.models import Config, Datos, Materia, Oferta, Profesor
from scheduler.optimizer import ortools_disponible, resolver
from scheduler.schedule_validator import validar_horario
from scheduler.service import revisar

pytestmark = pytest.mark.skipif(not ortools_disponible(), reason="requiere OR-Tools")


def _resolver(datos, **kw):
    sesiones, disp = preparar(datos)
    r = resolver(datos, sesiones, disp, limite=kw.pop("limite", 15), **kw)
    return r, sesiones, disp


def test_solucion_unica_o_trivial():
    d = datos_minimos()
    d.config.dias = ["lunes"]
    d.config.hora_inicio, d.config.hora_fin = 8, 12
    d.ofertas[0].horas_semanales = 4  # 2 sesiones de 2 h en un único día de 4 h: 8-10 y 10-12
    d.config.misma_materia_mismo_dia = "permitir"
    r, sesiones, disp = _resolver(d)
    assert r.estado == "OPTIMAL"
    assert sorted(a.inicio for a in r.asignaciones) == [8, 10]
    assert validar_horario(d, sesiones, r.asignaciones, disp) == []


def test_varias_soluciones_el_resultado_es_valido():
    d = datos_minimos()
    r, sesiones, disp = _resolver(d)
    assert r.estado in ("OPTIMAL", "FEASIBLE")
    assert len(r.asignaciones) == 2
    assert validar_horario(d, sesiones, r.asignaciones, disp) == []


def test_sesiones_de_dos_horas_ocupan_dos_bloques_y_no_pasan_de_las_18():
    d = datos_minimos()
    d.disponibilidad = [disp_fila("P1", "lunes", 16, 18), disp_fila("P1", "martes", 16, 18)]
    r, *_ = _resolver(d)
    assert r.estado in ("OPTIMAL", "FEASIBLE")
    assert all(a.inicio == 16 and a.duracion == 2 for a in r.asignaciones)


def test_materia_sin_profesor_compatible_es_infactible():
    d = datos_minimos()
    d.profesores[0].materias = set()
    r, *_ = _resolver(d)
    assert r.estado == "INFEASIBLE"


def test_disponibilidad_insuficiente_es_infactible():
    d = datos_minimos()
    d.disponibilidad = [disp_fila("P1", "lunes", 8, 10)]  # 2 h libres para 4 h
    r, *_ = _resolver(d)
    assert r.estado == "INFEASIBLE"


def test_dos_materias_un_solo_profesor_empalmadas_es_infactible():
    rev = revisar(ejemplo("datos_infactibles_solver.xlsx"))
    assert rev.ok
    r = resolver(rev.datos, rev.sesiones, rev.disp, limite=10)
    assert r.estado == "INFEASIBLE"


def test_grupos_distintos_no_comparten_profesor_a_la_misma_hora():
    d = datos_minimos()
    d.ofertas.append(Oferta("O2", "1B", "MAT", 4))
    r, sesiones, disp = _resolver(d)
    assert validar_horario(d, sesiones, r.asignaciones, disp) == []


def test_limite_de_horas_maximas_obliga_a_repartir_entre_profesores():
    d = datos_minimos()
    d.profesores[0].horas_maximas = 4
    d.profesores.append(Profesor("P2", "Luis", {"MAT"}, horas_objetivo=4, horas_maximas=4))
    d.ofertas.append(Oferta("O2", "1B", "MAT", 4))
    r, *_ = _resolver(d)
    assert r.estado in ("OPTIMAL", "FEASIBLE")
    por_prof = {}
    for a in r.asignaciones:
        por_prof[a.profesor_id] = por_prof.get(a.profesor_id, 0) + a.duracion
    assert por_prof == {"P1": 4, "P2": 4}


def test_un_solo_profesor_por_oferta():
    d = datos_minimos()
    d.profesores.append(Profesor("P2", "Luis", {"MAT"}))
    r, *_ = _resolver(d)
    assert len({a.profesor_id for a in r.asignaciones}) == 1


def test_continuidad_sin_huecos_cuando_es_posible():
    # Un profesor con tres clases de 1 h en tres grupos distintos: el óptimo no deja huecos.
    d = Datos(
        profesores=[Profesor("P1", "Ana", {"ING"}, horas_objetivo=3)],
        materias=[Materia("ING", "Inglés", 1)],
        ofertas=[Oferta(f"O{i}", g, "ING", 1) for i, g in enumerate(["1A", "1B", "1C"], 1)],
        config=Config(dias=["lunes"]),
    )
    r, *_ = _resolver(d)
    assert r.estado == "OPTIMAL"
    assert calcular_metricas(d, r.asignaciones)["huecos_profesores"] == 0


def test_prioridad_de_continuidad_para_menor_carga_objetivo():
    # Tres clases de 1 h, y ambos profesores solo pueden a las 08:00 y a las 10:00 (nunca a las 09:00),
    # con máximo de 2 h cada uno. Alguien tiene que dar 2 clases y por eso tendrá un hueco de 1 h.
    # El peso docente es 1000 // (1 + horas_objetivo): 333 para CHICO (objetivo 2) y 32 para GRANDE
    # (objetivo 30). Lo correcto es dejar el hueco a GRANDE y proteger a CHICO.
    libres = [("lunes", 8, 9), ("lunes", 10, 11)]
    d = Datos(
        profesores=[
            Profesor("CHICO", "Poca carga", {"ING"}, horas_objetivo=2, horas_maximas=2),
            Profesor("GRANDE", "Mucha carga", {"ING"}, horas_objetivo=30, horas_maximas=2),
        ],
        materias=[Materia("ING", "Inglés", 1)],
        ofertas=[Oferta("O1", "1A", "ING", 1), Oferta("O2", "1B", "ING", 1), Oferta("O3", "1C", "ING", 1)],
        disponibilidad=[disp_fila(p, dia, h1, h2) for p in ("CHICO", "GRANDE") for dia, h1, h2 in libres],
        config=Config(dias=["lunes"], hora_inicio=8, hora_fin=11),
    )
    r, *_ = _resolver(d)
    assert r.estado == "OPTIMAL"
    m = {f["id"]: f for f in calcular_metricas(d, r.asignaciones)["profesores"]}
    assert m["CHICO"]["huecos"] == 0 and m["CHICO"]["horas"] == 1
    assert m["GRANDE"]["huecos"] == 1 and m["GRANDE"]["horas"] == 2


def test_reproducibilidad_con_semilla_fija():
    d = datos_minimos()
    d.ofertas.append(Oferta("O2", "1B", "MAT", 4))
    d.config.semilla_busqueda = 42
    a1, *_ = _resolver(d)
    a2, *_ = _resolver(d)
    assert [(a.sesion_id, a.dia, a.inicio) for a in a1.asignaciones] == [(a.sesion_id, a.dia, a.inicio) for a in a2.asignaciones]


def test_ejemplo_valido_completo():
    rev = revisar(ejemplo("datos_validos.xlsx"))
    r = resolver(rev.datos, rev.sesiones, rev.disp, limite=30)
    assert r.estado in ("OPTIMAL", "FEASIBLE")
    assert len(r.asignaciones) == 48
    assert validar_horario(rev.datos, rev.sesiones, r.asignaciones, rev.disp) == []
