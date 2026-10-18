import entorno
from acceso.tokens import acceso_abierto

VARS = ("WEBSITES_PORT", "PORT", "WEBSITE_SITE_NAME", "WEBSITE_INSTANCE_ID", "SCHEDORA_ACCESO_ABIERTO")


def _limpio(monkeypatch):
    for v in VARS:
        monkeypatch.delenv(v, raising=False)


def test_puerto_local_por_defecto(monkeypatch):
    _limpio(monkeypatch)
    assert entorno.puerto() == 7860 and not entorno.en_azure()


def test_puerto_en_azure_sin_configurar_es_8000(monkeypatch):
    _limpio(monkeypatch)
    monkeypatch.setenv("WEBSITE_SITE_NAME", "schedora")
    assert entorno.en_azure() and entorno.puerto() == 8000


def test_websites_port_tiene_prioridad(monkeypatch):
    _limpio(monkeypatch)
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("WEBSITES_PORT", "8123")
    assert entorno.puerto() == 8123


def test_puerto_invalido_se_ignora(monkeypatch):
    _limpio(monkeypatch)
    monkeypatch.setenv("WEBSITES_PORT", "abc")
    assert entorno.puerto() == 7860


def test_acceso_abierto_funciona_en_local(monkeypatch):
    _limpio(monkeypatch)
    monkeypatch.setenv("SCHEDORA_ACCESO_ABIERTO", "1")
    assert acceso_abierto()


def test_acceso_abierto_se_ignora_en_azure(monkeypatch):
    _limpio(monkeypatch)
    monkeypatch.setenv("SCHEDORA_ACCESO_ABIERTO", "1")
    monkeypatch.setenv("WEBSITE_SITE_NAME", "schedora")
    assert not acceso_abierto()
