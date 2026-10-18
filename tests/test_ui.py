"""Pruebas de la capa de interfaz que no necesitan arrancar Gradio."""
import os
import shutil

import pytest

from helpers import ejemplo
from scheduler.models import Datos, Problema
from scheduler.service import Revision, revisar
from ui import callbacks as cb
from ui import render


def test_el_texto_del_archivo_se_escapa_en_el_html():
    rev = Revision(Datos(), [Problema("error", "PROFESORES", 3, "<script>alert(1)</script>")])
    html = render.revision_html(rev)
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_revision_correcta_muestra_resumen():
    html = render.revision_html(revisar(ejemplo("datos_validos.xlsx")))
    assert "Tu archivo está en orden" in html and "grupos" in html


def test_revision_con_errores_indica_hoja_y_cantidad():
    html = render.revision_html(revisar(ejemplo("datos_infactibles.xlsx")))
    assert "por corregir" in html and "OFERTA_ACADEMICA" in html


def test_los_mensajes_no_dependen_solo_del_color():
    for clase, icono in (("ok", "✓"), ("warn", "!"), ("err", "×"), ("info", "i")):
        assert icono in render.banner(clase, "Titulo")


def test_acceso_invalido_no_abre_la_aplicacion(monkeypatch):
    monkeypatch.delenv("SCHEDORA_ACCESO_ABIERTO", raising=False)
    monkeypatch.setenv("SCHEDORA_SECRET", "secreto-de-prueba-largo-123")
    monkeypatch.setattr(cb.time, "sleep", lambda s: None)
    token, compuerta, app, msg, _ = cb.entrar("SCH-AAAA-AAAA-AAAA-AAAA-AAAA-AAAA")
    assert token is None and app["visible"] is False and compuerta["visible"] is True and "No reconocemos" in msg


def test_acceso_valido_abre_la_aplicacion(monkeypatch):
    from acceso.tokens import crear_codigo, fin_de_dia_unix, obtener_secreto

    monkeypatch.delenv("SCHEDORA_ACCESO_ABIERTO", raising=False)
    monkeypatch.setenv("SCHEDORA_SECRET", "secreto-de-prueba-largo-123")
    codigo, _ = crear_codigo(obtener_secreto(), fin_de_dia_unix(2))
    token, compuerta, app, msg, banner = cb.entrar(codigo)
    assert token == codigo and app["visible"] is True and "Acceso activo hasta" in banner


def test_un_acceso_revocado_deja_de_funcionar_a_media_sesion(monkeypatch):
    from acceso.tokens import crear_codigo, fin_de_dia_unix, obtener_secreto

    monkeypatch.delenv("SCHEDORA_ACCESO_ABIERTO", raising=False)
    monkeypatch.setenv("SCHEDORA_SECRET", "secreto-de-prueba-largo-123")
    codigo, id_hex = crear_codigo(obtener_secreto(), fin_de_dia_unix(2))
    monkeypatch.setenv("SCHEDORA_REVOCADOS", id_hex)
    resultado = cb.revisar_archivo("/da/igual.xlsx", codigo)
    assert resultado[0] is None and "ya no está activo" in resultado[1]
    assert cb.generar_horario(object(), 30, codigo)[0] is None


def test_sin_token_no_se_puede_usar_la_aplicacion(monkeypatch):
    monkeypatch.delenv("SCHEDORA_ACCESO_ABIERTO", raising=False)
    assert cb.revisar_archivo(ejemplo("datos_validos.xlsx"), None)[0] is None


def test_revisar_borra_el_archivo_subido(tmp_path, monkeypatch):
    monkeypatch.setenv("SCHEDORA_ACCESO_ABIERTO", "1")
    copia = tmp_path / "subido.xlsx"
    shutil.copy(ejemplo("datos_validos.xlsx"), copia)
    rev, html, boton, *_ = cb.revisar_archivo(str(copia), "abierto")
    assert rev.ok and boton["interactive"] is True and not os.path.exists(copia)


def test_revision_con_errores_deja_el_boton_generar_apagado_y_ofrece_reporte(tmp_path, monkeypatch):
    monkeypatch.setenv("SCHEDORA_ACCESO_ABIERTO", "1")
    copia = tmp_path / "malo.xlsx"
    shutil.copy(ejemplo("datos_infactibles.xlsx"), copia)
    rev, html, boton, diag, _ = cb.revisar_archivo(str(copia), "abierto")
    assert not rev.ok and boton["interactive"] is False and diag["visible"] is True and os.path.exists(diag["value"])


def test_logo_de_la_carpeta_principal_tiene_prioridad(tmp_path, monkeypatch):
    from ui import tema

    raiz, assets = tmp_path, tmp_path / "assets"
    assets.mkdir()
    (assets / "schedora-logo.svg").write_text("<svg/>")
    (raiz / "logo.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(tema, "_RAIZ", str(raiz))
    monkeypatch.setattr(tema, "ASSETS", str(assets))
    assert tema._data_uri("schedora-logo.svg").startswith("data:image/png;base64,")
    (raiz / "logo.png").unlink()
    assert tema._data_uri("schedora-logo.svg").startswith("data:image/svg+xml;base64,")
    assert tema._data_uri("no-existe-logo.svg") == ""
