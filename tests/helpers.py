"""Utilidades de prueba.

`horario_voraz` arma un horario con un algoritmo simple (sin OR-Tools) para poder
probar el validador, las métricas y el exportador de forma aislada del optimizador.
Funciona con los datos holgados de examples/datos_validos.xlsx; no es el motor real.
"""
from __future__ import annotations

import os
from collections import defaultdict

from scheduler.availability import calcular_disponibilidad, inicios_validos
from scheduler.models import Asignacion, Config, Datos, FilaDisponibilidad, Materia, Oferta, Profesor
from scheduler.session_builder import construir_sesiones

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EJEMPLOS = os.path.join(RAIZ, "examples")


def ejemplo(nombre: str) -> str:
    return os.path.join(EJEMPLOS, nombre)


def datos_minimos() -> Datos:
    """Un colegio mínimo y válido: 1 profesor de MAT (2 h/sesión), 1 grupo, 4 h semanales."""
    return Datos(
        profesores=[Profesor("P1", "Ana", {"MAT"}, horas_objetivo=4)],
        materias=[Materia("MAT", "Matemáticas", 2)],
        ofertas=[Oferta("O1", "1A", "MAT", 4)],
        config=Config(),
    )


def preparar(datos: Datos):
    """(sesiones, disponibilidad) para unos datos ya válidos."""
    sesiones, problemas = construir_sesiones(datos)
    assert not problemas, problemas
    return sesiones, calcular_disponibilidad(datos)


def disp_fila(pid, dia, h1, h2, tipo="DISPONIBLE") -> FilaDisponibilidad:
    return FilaDisponibilidad(pid, dia, h1, h2, tipo, fila=2)


def horario_voraz(datos, sesiones, disp) -> list[Asignacion]:
    cfg = datos.config
    ofertas = {o.id: o for o in datos.ofertas}
    ocup_p: set = set()
    ocup_g: set = set()
    prof_de_oferta: dict = {}
    dias_de_oferta: dict = defaultdict(set)
    asignaciones: list[Asignacion] = []
    for s in sorted(sesiones, key=lambda s: (-s.duracion, s.id)):
        o = ofertas[s.oferta_id]
        if o.id in prof_de_oferta:
            cand = [prof_de_oferta[o.id]]
        elif o.profesor_obligatorio:
            cand = [o.profesor_obligatorio]
        else:
            cand = [p.id for p in datos.profesores if p.activo and s.materia in p.materias]
        colocada = False
        for pid in cand:
            for d in range(len(cfg.dias)):
                if d in dias_de_oferta[o.id]:
                    continue
                for t in inicios_validos(disp[pid], d, s.duracion, cfg):
                    bloques = range(t, t + s.duracion)
                    if any((pid, d, h) in ocup_p or (s.grupo, d, h) in ocup_g for h in bloques):
                        continue
                    for h in bloques:
                        ocup_p.add((pid, d, h))
                        ocup_g.add((s.grupo, d, h))
                    prof_de_oferta[o.id] = pid
                    dias_de_oferta[o.id].add(d)
                    asignaciones.append(Asignacion(s.id, s.oferta_id, s.grupo, s.materia, pid, cfg.dias[d], t, s.duracion))
                    colocada = True
                    break
                if colocada:
                    break
            if colocada:
                break
        if not colocada:
            raise AssertionError(f"El voraz no pudo ubicar {s.id}")
    return asignaciones
