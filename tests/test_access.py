import time

from acceso.tokens import (
    crear_codigo,
    fin_de_dia_unix,
    obtener_revocados,
    obtener_secreto,
    verificar_codigo,
)

SECRETO = b"secreto-de-prueba-bastante-largo"
ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def _codigo(dias=3):
    return crear_codigo(SECRETO, fin_de_dia_unix(dias))


def test_codigo_valido():
    codigo, id_hex = _codigo()
    r = verificar_codigo(codigo, SECRETO, set())
    assert r.valido and r.id == id_hex and r.vence > time.time()


def test_formato_flexible_minusculas_espacios_sin_guiones():
    codigo, _ = _codigo()
    suelto = codigo.lower().replace("-", " ")
    assert verificar_codigo(suelto, SECRETO, set()).valido
    assert verificar_codigo(codigo.replace("-", ""), SECRETO, set()).valido


def test_cualquier_alteracion_se_rechaza():
    codigo, _ = _codigo()
    cuerpo = codigo.replace("-", "")[3:]
    for i, ch in enumerate(cuerpo):
        otro = ALFABETO[(ALFABETO.index(ch) + 1) % 32]
        alterado = "SCH" + cuerpo[:i] + otro + cuerpo[i + 1 :]
        assert not verificar_codigo(alterado, SECRETO, set()).valido, f"posición {i}"


def test_vencido():
    codigo, _ = _codigo(dias=1)
    r = verificar_codigo(codigo, SECRETO, set(), ahora=time.time() + 5 * 86400)
    assert not r.valido and "terminó" in r.mensaje


def test_vigente_hasta_el_ultimo_segundo_del_dia():
    vence = fin_de_dia_unix(2)
    codigo, _ = crear_codigo(SECRETO, vence)
    assert verificar_codigo(codigo, SECRETO, set(), ahora=vence).valido
    assert not verificar_codigo(codigo, SECRETO, set(), ahora=vence + 1).valido


def test_revocado_antes_de_vencer():
    codigo, id_hex = _codigo()
    r = verificar_codigo(codigo, SECRETO, {id_hex})
    assert not r.valido and "desactivado" in r.mensaje


def test_secreto_distinto_no_acepta():
    codigo, _ = _codigo()
    assert not verificar_codigo(codigo, b"otro-secreto-completamente-distinto", set()).valido


def test_basura():
    for basura in ["", "hola", "SCH-AAAA", "!!!!", "SCH-" + "A" * 24, "SCH-" + "1" * 24]:
        assert not verificar_codigo(basura, SECRETO, set()).valido


def test_falla_cerrado_sin_secreto(monkeypatch):
    monkeypatch.delenv("SCHEDORA_SECRET", raising=False)
    assert obtener_secreto() is None
    codigo, _ = _codigo()
    r = verificar_codigo(codigo)
    assert not r.valido and "configurado" in r.mensaje


def test_secreto_corto_se_considera_no_configurado(monkeypatch):
    monkeypatch.setenv("SCHEDORA_SECRET", "corto")
    assert obtener_secreto() is None


def test_revocados_desde_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("SCHEDORA_REVOCADOS", " A1B2C3D4 , e5f6a7b8;11223344 ")
    assert obtener_revocados() == {"a1b2c3d4", "e5f6a7b8", "11223344"}


def test_los_codigos_emitidos_son_distintos():
    assert _codigo()[0] != _codigo()[0]
