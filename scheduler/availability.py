"""Interpretación de la disponibilidad docente.

Reglas (documentadas en docs/modelo_datos.md):
1. Sin filas para un profesor  -> disponible en todo el calendario.
2. Con filas DISPONIBLE        -> solo esos intervalos (lista blanca).
3. Solo filas NO_DISPONIBLE    -> todo el calendario menos esos intervalos.
4. NO_DISPONIBLE siempre prevalece sobre DISPONIBLE si se cruzan.
"""
from __future__ import annotations

from .models import Datos

Bloque = tuple[int, int]  # (indice_de_dia, hora)


def calcular_disponibilidad(datos: Datos) -> dict[str, set[Bloque]]:
    """Devuelve {profesor_id: {(indice_dia, hora), ...}} para cada profesor (activo o no)."""
    cfg = datos.config
    indice_dia = {d: i for i, d in enumerate(cfg.dias)}
    calendario = {(i, h) for i in range(len(cfg.dias)) for h in cfg.horas_calendario}

    filas_por_prof: dict[str, list] = {}
    for f in datos.disponibilidad:
        filas_por_prof.setdefault(f.profesor_id, []).append(f)

    def bloques(f) -> set[Bloque]:
        if f.dia not in indice_dia or f.hora_inicio >= f.hora_fin:
            return set()
        return {(indice_dia[f.dia], h) for h in range(f.hora_inicio, f.hora_fin)} & calendario

    resultado: dict[str, set[Bloque]] = {}
    for p in datos.profesores:
        filas = filas_por_prof.get(p.id, [])
        blancos = [f for f in filas if f.tipo == "DISPONIBLE"]
        negros = [f for f in filas if f.tipo == "NO_DISPONIBLE"]
        if blancos:
            disp: set[Bloque] = set()
            for f in blancos:
                disp |= bloques(f)
        else:
            disp = set(calendario)
        for f in negros:
            disp -= bloques(f)
        resultado[p.id] = disp
    return resultado


def inicios_validos(disponibles: set[Bloque], dia_idx: int, duracion: int, cfg) -> list[int]:
    """Horas de inicio t tales que t..t+duracion-1 están libres ese día y caben antes del fin."""
    return [
        t
        for t in range(cfg.hora_inicio, cfg.hora_fin - duracion + 1)
        if all((dia_idx, t + k) in disponibles for k in range(duracion))
    ]
