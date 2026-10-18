"""Punto de entrada de Schedora.

Local:   SCHEDORA_ACCESO_ABIERTO=1 python app.py     (sin código de acceso, solo desarrollo)
Azure:   python app.py                                (requiere SCHEDORA_SECRET; ver docs/despliegue.md)
"""
import logging
import os

from entorno import puerto
from ui.components import construir_app

logging.basicConfig(level=os.environ.get("SCHEDORA_LOG", "INFO"), format="%(asctime)s %(name)s %(levelname)s %(message)s")


def main() -> None:
    demo, lanzamiento = construir_app()
    demo.launch(
        server_name="0.0.0.0",
        server_port=puerto(),
        **lanzamiento,
    )


if __name__ == "__main__":
    main()
