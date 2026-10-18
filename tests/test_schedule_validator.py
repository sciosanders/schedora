import dataclasses

import pytest

from helpers import ejemplo, horario_voraz
from scheduler.schedule_validator import validar_horario
from scheduler.service import revisar


@pytest.fixture(scope="module")
def base():
    rev = revisar(ejemplo("datos_validos.xlsx"))
    asignaciones = horario_voraz(rev.datos, rev.sesiones, rev.disp)
    return rev, asignaciones


def _validar(base, asignaciones):
    rev, _ = base
    return validar_horario(rev.datos, rev.sesiones, asignaciones, rev.disp)


def _reemplazar(asignaciones, i, **cambios):
    out = list(asignaciones)
    out[i] = dataclasses.replace(out[i], **cambios)
    return out


def test_horario_correcto_pasa(base):
    assert _validar(base, base[1]) == []


def test_sesion_faltante(base):
    assert any("sin programar" in e for e in _validar(base, base[1][1:]))


def test_sesion_duplicada(base):
    assert any("programada 2 veces" in e for e in _validar(base, base[1] + [base[1][0]]))


def test_empalme_docente(base):
    _, a = base
    x = a[0]
    i = next(i for i, z in enumerate(a) if z.profesor_id == x.profesor_id and z.grupo != x.grupo)
    errores = _validar(base, _reemplazar(a, i, dia=x.dia, inicio=x.inicio))
    assert any("Empalme docente" in e for e in errores)


def test_empalme_de_grupo(base):
    _, a = base
    x = a[0]
    i = next(i for i, z in enumerate(a) if z.grupo == x.grupo and z.profesor_id != x.profesor_id)
    errores = _validar(base, _reemplazar(a, i, dia=x.dia, inicio=x.inicio))
    assert any("Empalme de grupo" in e for e in errores)


def test_sesion_que_excede_las_18(base):
    _, a = base
    i = next(i for i, z in enumerate(a) if z.duracion == 2)
    errores = _validar(base, _reemplazar(a, i, inicio=17))
    assert any("sale del horario" in e for e in errores)


def test_profesor_no_capacitado(base):
    _, a = base
    i = next(i for i, z in enumerate(a) if z.materia == "MAT")
    errores = _validar(base, _reemplazar(a, i, profesor_id="P02"))
    assert any("no está capacitado" in e for e in errores)


def test_profesor_inactivo(base):
    _, a = base
    i = next(i for i, z in enumerate(a) if z.materia == "MAT")
    errores = _validar(base, _reemplazar(a, i, profesor_id="P06"))
    assert any("inactivo" in e for e in errores)


def test_fuera_de_la_disponibilidad(base):
    _, a = base
    i = next(i for i, z in enumerate(a) if z.profesor_id == "P05")  # solo L, M, V de 08 a 12
    errores = _validar(base, _reemplazar(a, i, dia="sabado", inicio=8))
    assert any("no está disponible" in e for e in errores)


def test_duracion_incorrecta(base):
    _, a = base
    i = next(i for i, z in enumerate(a) if z.duracion == 2)
    errores = _validar(base, _reemplazar(a, i, duracion=1))
    assert any("duración" in e for e in errores)


def test_dos_profesores_en_una_oferta(base):
    rev, a = base
    # P03 (ING, HIS) y... ING solo la imparte P03; se fuerza otro profesor que sí la tenga:
    rev.datos.profesor("P05").materias.add("EDF")  # ya la tiene; la oferta EDF solo la da P05
    i = next(i for i, z in enumerate(a) if z.materia == "MAT")
    rev.datos.profesor("P04").materias.add("MAT")
    try:
        errores = _validar(base, _reemplazar(a, i, profesor_id="P04"))
    finally:
        rev.datos.profesor("P04").materias.discard("MAT")
    assert any("la imparten varios profesores" in e for e in errores)


def test_horas_maximas(base):
    rev, a = base
    anterior = rev.datos.profesor("P01").horas_maximas
    rev.datos.profesor("P01").horas_maximas = 2
    try:
        errores = _validar(base, a)
    finally:
        rev.datos.profesor("P01").horas_maximas = anterior
    assert any("su máximo es 2" in e for e in errores)


def test_horas_minimas(base):
    rev, a = base
    anterior = rev.datos.profesor("P05").horas_minimas
    rev.datos.profesor("P05").horas_minimas = 20
    try:
        errores = _validar(base, a)
    finally:
        rev.datos.profesor("P05").horas_minimas = anterior
    assert any("su mínimo es 20" in e for e in errores)


def test_misma_materia_mismo_dia_solo_si_es_obligatoria(base):
    rev, a = base
    # dos sesiones de la misma oferta el mismo día
    mat = [i for i, z in enumerate(a) if z.oferta_id == a[0].oferta_id]
    assert len(mat) >= 2
    movida = _reemplazar(a, mat[1], dia=a[mat[0]].dia, inicio=a[mat[0]].inicio + 2 if a[mat[0]].inicio + 4 <= 18 else a[mat[0]].inicio - 2)
    rev.datos.config.misma_materia_mismo_dia = "obligatorio"
    try:
        errores = _validar(base, movida)
    finally:
        rev.datos.config.misma_materia_mismo_dia = "evitar"
    assert any("la regla es obligatoria" in e for e in errores)
