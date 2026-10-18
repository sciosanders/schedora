"""Regenera los libros de ejemplo. Uso:  python examples/make_examples.py"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from scheduler import plantilla  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    plantilla.crear_plantilla(os.path.join(AQUI, "plantilla_horarios.xlsx"))
    plantilla.crear_ejemplo_valido(os.path.join(AQUI, "datos_validos.xlsx"))
    plantilla.crear_ejemplo_infactible(os.path.join(AQUI, "datos_infactibles.xlsx"))
    plantilla.crear_ejemplo_infactible_solver(os.path.join(AQUI, "datos_infactibles_solver.xlsx"))
    print("Ejemplos generados en", AQUI)
