from helpers import datos_minimos
from scheduler.models import Materia, Oferta
from scheduler.session_builder import construir_sesiones


def test_4_horas_con_sesiones_de_2_son_2_sesiones():
    sesiones, problemas = construir_sesiones(datos_minimos())
    assert not problemas
    assert [s.id for s in sesiones] == ["O1#1", "O1#2"]
    assert all(s.duracion == 2 and s.grupo == "1A" for s in sesiones)


def test_sesiones_de_1_hora():
    d = datos_minimos()
    d.materias.append(Materia("ING", "Inglés", 1))
    d.ofertas.append(Oferta("O2", "1A", "ING", 3))
    sesiones, _ = construir_sesiones(d)
    assert len([s for s in sesiones if s.oferta_id == "O2"]) == 3


def test_no_se_inventan_ni_se_redondean_horas():
    d = datos_minimos()
    d.ofertas[0].horas_semanales = 3
    sesiones, problemas = construir_sesiones(d)
    assert sesiones == [] and problemas and problemas[0].es_error


def test_sesiones_semanales_inconsistentes():
    d = datos_minimos()
    d.ofertas[0].sesiones_semanales = 5
    sesiones, problemas = construir_sesiones(d)
    assert sesiones == [] and "no coincide" in problemas[0].mensaje


def test_total_de_horas_de_los_ejemplos():
    from helpers import ejemplo
    from scheduler.service import revisar

    rev = revisar(ejemplo("datos_validos.xlsx"))
    assert len(rev.sesiones) == 48 and sum(s.duracion for s in rev.sesiones) == 76
