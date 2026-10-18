import shutil

import pytest
from openpyxl import Workbook

from helpers import ejemplo
from scheduler.excel_reader import leer_excel
from scheduler.models import ErrorArchivo


def _libro(tmp_path, hojas: dict, nombre="libro.xlsx"):
    wb = Workbook()
    wb.remove(wb.active)
    for titulo, filas in hojas.items():
        ws = wb.create_sheet(titulo)
        for f in filas:
            ws.append(f)
    ruta = tmp_path / nombre
    wb.save(ruta)
    return str(ruta)


BASE = {
    "PROFESORES": [["profesor_id", "nombre", "materias"], ["P1", "Ana", "MAT"]],
    "MATERIAS": [["materia_id", "nombre_materia", "duracion_sesion"], ["MAT", "Matemáticas", 2]],
    "OFERTA_ACADEMICA": [["oferta_id", "grupo_id", "materia_id", "horas_semanales"], ["O1", "1A", "MAT", 4]],
}


def test_excel_valido_se_lee_completo():
    datos, problemas = leer_excel(ejemplo("datos_validos.xlsx"))
    assert not [p for p in problemas if p.es_error]
    assert len(datos.profesores) == 6
    assert len(datos.materias) == 6
    assert len(datos.ofertas) == 24
    assert len(datos.disponibilidad) == 6
    assert datos.profesor("P06").activo is False
    assert datos.profesor("P03").materias == {"ING", "HIS"}


def test_hoja_ausente(tmp_path):
    ruta = _libro(tmp_path, {"PROFESORES": BASE["PROFESORES"]})
    _, problemas = leer_excel(ruta)
    mensajes = [str(p) for p in problemas]
    assert any("Falta la hoja «MATERIAS»" in m for m in mensajes)
    assert any("Falta la hoja «OFERTA_ACADEMICA»" in m for m in mensajes)


def test_columna_obligatoria_ausente(tmp_path):
    hojas = dict(BASE)
    hojas["MATERIAS"] = [["materia_id", "nombre_materia"], ["MAT", "Matemáticas"]]
    _, problemas = leer_excel(_libro(tmp_path, hojas))
    assert any("duracion_sesion" in p.mensaje and p.hoja == "MATERIAS" for p in problemas)


def test_nombres_de_hoja_y_columna_son_flexibles(tmp_path):
    hojas = {
        "profesores": [["Profesor ID", "Nombre", "Materias"], ["P1", "Ana", "MAT"]],
        "Materias": [["materia_id", "Nombre Materia", "Duración Sesion"], ["MAT", "Matemáticas", 2]],
        "oferta academica": [["Oferta ID", "Grupo ID", "Materia ID", "Horas Semanales"], ["O1", "1A", "MAT", 4]],
    }
    datos, problemas = leer_excel(_libro(tmp_path, hojas))
    assert not [p for p in problemas if p.es_error], problemas
    assert datos.ofertas[0].horas_semanales == 4


def test_hora_que_no_es_en_punto_se_reporta_con_fila(tmp_path):
    hojas = dict(BASE)
    hojas["DISPONIBILIDAD"] = [
        ["profesor_id", "dia", "hora_inicio", "hora_fin", "tipo"],
        ["P1", "lunes", "08:30", "10:00", "DISPONIBLE"],
    ]
    _, problemas = leer_excel(_libro(tmp_path, hojas))
    p = next(p for p in problemas if p.hoja == "DISPONIBILIDAD")
    assert p.es_error and p.fila == 2 and "en punto" in p.mensaje


def test_dia_y_tipo_invalidos(tmp_path):
    hojas = dict(BASE)
    hojas["DISPONIBILIDAD"] = [
        ["profesor_id", "dia", "hora_inicio", "hora_fin", "tipo"],
        ["P1", "domingo", "08:00", "10:00", "DISPONIBLE"],
        ["P1", "lunes", "08:00", "10:00", "QUIZA"],
    ]
    _, problemas = leer_excel(_libro(tmp_path, hojas))
    assert len([p for p in problemas if p.es_error]) == 2


def test_numero_no_entero_en_horas(tmp_path):
    hojas = dict(BASE)
    hojas["OFERTA_ACADEMICA"] = [["oferta_id", "grupo_id", "materia_id", "horas_semanales"], ["O1", "1A", "MAT", 3.5]]
    _, problemas = leer_excel(_libro(tmp_path, hojas))
    assert any("entero" in p.mensaje for p in problemas)


def test_xlsm_se_rechaza(tmp_path):
    destino = tmp_path / "macro.xlsm"
    shutil.copy(ejemplo("datos_validos.xlsx"), destino)
    with pytest.raises(ErrorArchivo):
        leer_excel(str(destino))


def test_archivo_que_no_es_excel(tmp_path):
    falso = tmp_path / "falso.xlsx"
    falso.write_text("esto no es un excel")
    with pytest.raises(ErrorArchivo):
        leer_excel(str(falso))


def test_archivo_inexistente():
    with pytest.raises(ErrorArchivo):
        leer_excel("/no/existe.xlsx")


def test_formulas_no_se_evaluan(tmp_path):
    hojas = {k: [list(f) for f in v] for k, v in BASE.items()}
    hojas["PROFESORES"][1][1] = "=1+1"  # fórmula en «nombre»: no hay valor calculado guardado
    datos, _ = leer_excel(_libro(tmp_path, hojas))
    assert datos.profesores[0].nombre == "P1"  # se ignora la fórmula; nunca se ejecuta


def test_configuracion_se_lee(tmp_path):
    hojas = dict(BASE)
    hojas["CONFIGURACION"] = [
        ["clave", "valor"],
        ["hora_inicio", "08:00"],
        ["hora_fin", "14:00"],
        ["dias", "lunes a viernes"],
        ["limite_busqueda_segundos", 15],
        ["misma_materia_mismo_dia", "obligatorio"],
        ["semilla_busqueda", 7],
    ]
    datos, problemas = leer_excel(_libro(tmp_path, hojas))
    assert not [p for p in problemas if p.es_error], problemas
    c = datos.config
    assert (c.hora_inicio, c.hora_fin) == (8, 14)
    assert c.dias == ["lunes", "martes", "miercoles", "jueves", "viernes"]
    assert c.limite_busqueda_segundos == 15 and c.misma_materia_mismo_dia == "obligatorio" and c.semilla_busqueda == 7
