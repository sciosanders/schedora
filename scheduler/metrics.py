"""Métricas del horario: carga, huecos internos y continuidad."""
from __future__ import annotations

from collections import defaultdict

from .models import Asignacion, Datos


def _huecos_por_dia(bloques_por_dia: dict[int, set[int]]) -> int:
    """Horas libres ENTRE clases (no cuenta el tiempo libre al inicio o al final del día)."""
    total = 0
    for horas in bloques_por_dia.values():
        if len(horas) >= 2:
            total += (max(horas) - min(horas) + 1) - len(horas)
    return total


def calcular_metricas(datos: Datos, asignaciones: list[Asignacion]) -> dict:
    cfg = datos.config
    prof_bloques: dict[str, dict[int, set[int]]] = defaultdict(lambda: defaultdict(set))
    grupo_bloques: dict[str, dict[int, set[int]]] = defaultdict(lambda: defaultdict(set))
    horas_prof: dict[str, int] = defaultdict(int)
    horas_grupo: dict[str, int] = defaultdict(int)
    for a in asignaciones:
        d = cfg.dias.index(a.dia)
        for h in a.bloques:
            prof_bloques[a.profesor_id][d].add(h)
            grupo_bloques[a.grupo][d].add(h)
        horas_prof[a.profesor_id] += a.duracion
        horas_grupo[a.grupo] += a.duracion

    filas_prof = []
    dias_trabajados = 0
    dias_sin_hueco = 0
    for p in datos.profesores:
        if not p.activo:
            continue
        por_dia = prof_bloques.get(p.id, {})
        huecos = _huecos_por_dia(por_dia)
        for horas in por_dia.values():
            dias_trabajados += 1
            if len(horas) < 2 or (max(horas) - min(horas) + 1) == len(horas):
                dias_sin_hueco += 1
        filas_prof.append(
            {
                "id": p.id,
                "nombre": p.nombre,
                "horas_objetivo": p.horas_objetivo,
                "horas": horas_prof.get(p.id, 0),
                "dias": len(por_dia),
                "huecos": huecos,
            }
        )
    filas_grupo = [
        {"grupo": g, "horas": horas_grupo.get(g, 0), "huecos": _huecos_por_dia(grupo_bloques.get(g, {}))}
        for g in datos.grupos
    ]
    return {
        "profesores": filas_prof,
        "grupos": filas_grupo,
        "sesiones": len(asignaciones),
        "huecos_profesores": sum(f["huecos"] for f in filas_prof),
        "huecos_grupos": sum(f["huecos"] for f in filas_grupo),
        "dias_docentes_trabajados": dias_trabajados,
        "dias_docentes_sin_hueco": dias_sin_hueco,
        "continuidad_pct": round(100 * dias_sin_hueco / dias_trabajados) if dias_trabajados else 100,
    }
