"""Cuadrículas semanales (hora × día) por grupo o por profesor.

Las usan la interfaz (tabla en pantalla) y el exportador (hojas de Excel).
"""
from __future__ import annotations

from .models import NOMBRE_DIA, Asignacion, Datos


def etiqueta_materia(datos: Datos, mid: str) -> str:
    m = datos.materia(mid)
    return m.nombre if m else mid


def etiqueta_profesor(datos: Datos, pid: str) -> str:
    p = datos.profesor(pid)
    return p.nombre if p else pid


def entidades(datos: Datos, asignaciones: list[Asignacion], tipo: str) -> list[tuple[str, str]]:
    """Lista de (etiqueta, valor) para el selector. tipo: 'grupo' | 'profesor'."""
    if tipo == "grupo":
        return [(f"Grupo {g}", g) for g in datos.grupos]
    con_clases = {a.profesor_id for a in asignaciones}
    return [(p.nombre, p.id) for p in datos.profesores if p.id in con_clases]


def texto_celda(datos: Datos, a: Asignacion, tipo: str) -> str:
    materia = etiqueta_materia(datos, a.materia)
    if tipo == "grupo":
        return f"{materia} · {etiqueta_profesor(datos, a.profesor_id)}"
    return f"{materia} · Grupo {a.grupo}"


def cuadricula(datos: Datos, asignaciones: list[Asignacion], tipo: str, entidad: str):
    """Devuelve (encabezados, filas, ocupaciones).

    filas: lista de listas de texto, una por hora del calendario.
    ocupaciones: {(fila_idx, col_idx): (texto, duracion)} solo en la primera hora de cada clase,
    útil para combinar celdas en Excel.
    """
    cfg = datos.config
    encabezados = ["Hora"] + [NOMBRE_DIA.get(d, d.capitalize()) for d in cfg.dias]
    horas = cfg.horas_calendario
    filas = [[f"{h:02d}:00–{h + 1:02d}:00"] + [""] * len(cfg.dias) for h in horas]
    ocupaciones: dict[tuple[int, int], tuple[str, int]] = {}
    for a in asignaciones:
        if tipo == "grupo" and a.grupo != entidad:
            continue
        if tipo == "profesor" and a.profesor_id != entidad:
            continue
        col = cfg.dias.index(a.dia) + 1
        texto = texto_celda(datos, a, tipo)
        for k in range(a.duracion):
            fila = (a.inicio + k) - cfg.hora_inicio
            filas[fila][col] = texto
        ocupaciones[(a.inicio - cfg.hora_inicio, col)] = (texto, a.duracion)
    return encabezados, filas, ocupaciones
