from helpers import datos_minimos, disp_fila
from scheduler.availability import calcular_disponibilidad, inicios_validos

TOTAL = 6 * 11  # 6 días x (07:00-18:00)


def test_sin_filas_el_profesor_esta_libre_todo_el_calendario():
    d = datos_minimos()
    assert len(calcular_disponibilidad(d)["P1"]) == TOTAL


def test_solo_disponible_funciona_como_lista_blanca():
    d = datos_minimos()
    d.disponibilidad = [disp_fila("P1", "lunes", 8, 12)]
    disp = calcular_disponibilidad(d)["P1"]
    assert disp == {(0, 8), (0, 9), (0, 10), (0, 11)}


def test_solo_no_disponible_resta_del_calendario():
    d = datos_minimos()
    d.disponibilidad = [disp_fila("P1", "sabado", 7, 18, "NO_DISPONIBLE")]
    disp = calcular_disponibilidad(d)["P1"]
    assert len(disp) == TOTAL - 11 and not any(dia == 5 for dia, _ in disp)


def test_no_disponible_prevalece_si_se_cruza():
    d = datos_minimos()
    d.disponibilidad = [disp_fila("P1", "lunes", 8, 12), disp_fila("P1", "lunes", 9, 10, "NO_DISPONIBLE")]
    assert calcular_disponibilidad(d)["P1"] == {(0, 8), (0, 10), (0, 11)}


def test_intervalo_fuera_del_calendario_se_recorta():
    d = datos_minimos()
    d.disponibilidad = [disp_fila("P1", "lunes", 5, 9)]
    assert calcular_disponibilidad(d)["P1"] == {(0, 7), (0, 8)}


def test_inicios_validos_exigen_la_sesion_completa():
    d = datos_minimos()
    cfg = d.config
    libre = {(0, 8), (0, 9), (0, 11)}
    assert inicios_validos(libre, 0, 2, cfg) == [8]  # 8-9 sí; 9-10 no (falta 10); 11-12 no (falta 12)
    assert inicios_validos(libre, 0, 1, cfg) == [8, 9, 11]


def test_una_sesion_no_puede_pasar_de_las_18():
    d = datos_minimos()
    libre = {(0, 17)}
    assert inicios_validos(libre, 0, 1, d.config) == [17]
    assert inicios_validos({(0, 17), (0, 18)}, 0, 2, d.config) == []
