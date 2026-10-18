"""Detección del entorno de ejecución (local o Azure App Service) y puerto de escucha."""
import os


def en_azure() -> bool:
    """True dentro de Azure App Service (define WEBSITE_SITE_NAME / WEBSITE_INSTANCE_ID)."""
    return bool(os.environ.get("WEBSITE_SITE_NAME") or os.environ.get("WEBSITE_INSTANCE_ID"))


def puerto() -> int:
    """Puerto donde escuchar.

    Azure App Service (Linux) enruta al puerto indicado en WEBSITES_PORT; si no se define,
    espera 8000 en las imágenes de Python. Local: 7860 (el de Gradio).
    """
    for nombre in ("WEBSITES_PORT", "PORT"):
        valor = os.environ.get(nombre, "").strip()
        if valor.isdigit():
            return int(valor)
    return 8000 if en_azure() else 7860
