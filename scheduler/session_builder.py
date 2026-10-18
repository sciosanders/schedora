"""Convierte la oferta académica en sesiones individuales programables."""
from __future__ import annotations

from .models import Datos, Problema, Sesion


def construir_sesiones(datos: Datos) -> tuple[list[Sesion], list[Problema]]:
    """Una sesión por cada (horas_semanales / duracion). No redondea ni inventa horas.

    Las ofertas inconsistentes no generan sesiones y se reportan como error.
    """
    sesiones: list[Sesion] = []
    problemas: list[Problema] = []
    mat = {m.id: m for m in datos.materias}
    for o in datos.ofertas:
        m = mat.get(o.materia)
        if m is None or m.duracion not in (1, 2) or o.horas_semanales <= 0:
            problemas.append(Problema("error", "OFERTA_ACADEMICA", None, f"La oferta «{o.id}» no se puede convertir en sesiones."))
            continue
        if o.horas_semanales % m.duracion != 0:
            problemas.append(
                Problema(
                    "error",
                    "OFERTA_ACADEMICA",
                    None,
                    f"La oferta «{o.id}»: {o.horas_semanales} h no es múltiplo de la duración de sesión ({m.duracion} h).",
                )
            )
            continue
        n = o.horas_semanales // m.duracion
        if o.sesiones_semanales is not None and o.sesiones_semanales != n:
            problemas.append(
                Problema(
                    "error",
                    "OFERTA_ACADEMICA",
                    None,
                    f"La oferta «{o.id}»: sesiones_semanales={o.sesiones_semanales} no coincide con {n} calculadas.",
                )
            )
            continue
        for i in range(1, n + 1):
            sesiones.append(
                Sesion(id=f"{o.id}#{i}", oferta_id=o.id, grupo=o.grupo, materia=o.materia, duracion=m.duracion, indice=i)
            )
    return sesiones, problemas
