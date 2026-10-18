import dataclasses

from helpers import datos_minimos, disp_fila
from scheduler.models import Materia, Oferta, Profesor
from scheduler.validator import validar_datos


def _errores(datos):
    return [p.mensaje for p in validar_datos(datos) if p.es_error]


def _advertencias(datos):
    return [p.mensaje for p in validar_datos(datos) if not p.es_error]


def test_datos_minimos_son_validos():
    assert validar_datos(datos_minimos()) == []


def test_identificadores_duplicados():
    d = datos_minimos()
    d.profesores.append(Profesor("P1", "Otra", {"MAT"}))
    d.materias.append(Materia("MAT", "Otra", 1))
    d.ofertas.append(Oferta("O1", "1B", "MAT", 2))
    e = " ".join(_errores(d))
    assert "profesor_id duplicado" in e and "materia_id duplicado" in e and "oferta_id duplicado" in e


def test_materia_desconocida_en_oferta_y_en_profesor():
    d = datos_minimos()
    d.ofertas.append(Oferta("O2", "1A", "XXX", 2))
    d.profesores[0].materias.add("YYY")
    e = " ".join(_errores(d))
    assert "«XXX»" in e and "«YYY»" in e


def test_profesor_desconocido_en_disponibilidad_y_obligatorio():
    d = datos_minimos()
    d.disponibilidad.append(disp_fila("NOEXISTE", "lunes", 8, 10))
    d.ofertas[0].profesor_obligatorio = "FANTASMA"
    e = " ".join(_errores(d))
    assert "NOEXISTE" in e and "FANTASMA" in e


def test_duracion_invalida():
    d = datos_minimos()
    d.materias[0] = dataclasses.replace(d.materias[0], duracion=3)
    assert any("1 o 2 horas" in m for m in _errores(d))


def test_frecuencia_incompatible_con_duracion_no_se_redondea():
    d = datos_minimos()
    d.ofertas[0].horas_semanales = 3  # 3 h con sesiones de 2 h
    e = _errores(d)
    assert any("no es múltiplo" in m and "no se redondea" in m for m in e)


def test_sesiones_semanales_que_no_suman():
    d = datos_minimos()
    d.ofertas[0].sesiones_semanales = 3  # 3 x 2 h != 4 h
    assert any("no suman" in m for m in _errores(d))


def test_horas_semanales_no_positivas():
    d = datos_minimos()
    d.ofertas[0].horas_semanales = 0
    assert any("positivas" in m for m in _errores(d))


def test_minimo_mayor_que_maximo():
    d = datos_minimos()
    d.profesores[0].horas_minimas, d.profesores[0].horas_maximas = 10, 6
    assert any("mínimas" in m and "máximas" in m for m in _errores(d))


def test_intervalo_invertido_y_fuera_del_calendario():
    d = datos_minimos()
    d.disponibilidad.append(disp_fila("P1", "lunes", 12, 10))
    d.disponibilidad.append(disp_fila("P1", "martes", 6, 9))
    assert any("anterior" in m for m in _errores(d))
    assert any("sale del calendario" in m for m in _advertencias(d))


def test_disponibilidad_contradictoria_es_advertencia():
    d = datos_minimos()
    d.disponibilidad += [disp_fila("P1", "lunes", 8, 12), disp_fila("P1", "lunes", 10, 11, "NO_DISPONIBLE")]
    assert any("prevalece NO_DISPONIBLE" in m for m in _advertencias(d))


def test_profesor_obligatorio_sin_la_materia_o_inactivo():
    d = datos_minimos()
    d.profesores.append(Profesor("P2", "Luis", {"ESP"}))
    d.materias.append(Materia("ESP", "Español", 1))
    d.ofertas[0].profesor_obligatorio = "P2"
    assert any("no tiene la materia" in m for m in _errores(d))
    d.profesores[1].materias.add("MAT")
    d.profesores[1].activo = False
    assert any("inactivo" in m for m in _errores(d))


def test_libro_vacio():
    from scheduler.models import Datos

    e = " ".join(_errores(Datos()))
    assert "No hay profesores activos" in e and "No hay materias" in e and "No hay oferta" in e
