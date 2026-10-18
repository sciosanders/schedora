"""Diagnósticos: detección previa (sin solver) y análisis tras INFEASIBLE.

Principio del plan: no afirmar una causa específica si solo se sabe que el conjunto
de restricciones es incompatible. Por eso el análisis posterior dice «si se relaja X,
sí existe un horario», lo cual es un hecho comprobado, y no «X es la causa».
"""
from __future__ import annotations

from collections import Counter, defaultdict

from .availability import inicios_validos
from .models import Datos, Problema, Sesion
from . import optimizer


def _nombre_prof(datos: Datos, pid: str) -> str:
    p = datos.profesor(pid)
    return f"{p.nombre} ({pid})" if p and p.nombre != pid else pid


def verificaciones_previas(datos: Datos, sesiones: list[Sesion], disp: dict) -> list[Problema]:
    """Errores evidentes que hacen imposible el horario, detectables sin ejecutar el solver.

    Son condiciones necesarias: si alguna falla, no puede existir horario. Que todas
    pasen NO garantiza que exista uno.
    """
    out: list[Problema] = []
    cfg = datos.config
    n_dias = len(cfg.dias)
    h0, h1 = cfg.hora_inicio, cfg.hora_fin
    activos = {p.id: p for p in datos.profesores if p.activo}
    mat = {m.id: m for m in datos.materias}

    def err(hoja, msg):
        out.append(Problema("error", hoja, None, msg))

    def candidatos(o):
        if o.profesor_obligatorio:
            p = activos.get(o.profesor_obligatorio)
            return [p.id] if p and o.materia in p.materias else []
        return [pid for pid, p in activos.items() if o.materia in p.materias]

    # 1) Materias sin profesor elegible y ofertas sin franja libre compatible.
    for o in datos.ofertas:
        m = mat.get(o.materia)
        if m is None:
            continue
        cand = candidatos(o)
        if not cand:
            if not o.profesor_obligatorio:
                err(
                    "OFERTA_ACADEMICA",
                    f"Nadie puede impartir «{m.nombre}» (oferta {o.id}, grupo {o.grupo}): ningún profesor activo "
                    "tiene esa materia en su lista.",
                )
            continue
        if o.dias_permitidos:
            dias_ok = [i for i, d in enumerate(cfg.dias) if d in o.dias_permitidos]
        else:
            dias_ok = list(range(n_dias))
        hay_franja = any(inicios_validos(disp[pid], d, m.duracion, cfg) for pid in cand for d in dias_ok)
        if not hay_franja:
            nombres = ", ".join(_nombre_prof(datos, pid) for pid in cand)
            err(
                "DISPONIBILIDAD",
                f"La oferta {o.id} («{m.nombre}», grupo {o.grupo}) necesita sesiones de {m.duracion} h seguidas, "
                f"pero ninguno de sus profesores posibles ({nombres}) tiene una franja libre así en los días "
                "permitidos. Revisa la hoja DISPONIBILIDAD.",
            )

    # 2) Un grupo no puede pedir más horas de las que tiene el calendario.
    horas_grupo: Counter = Counter()
    for s in sesiones:
        horas_grupo[s.grupo] += s.duracion
    capacidad_grupo = n_dias * (h1 - h0)
    for g, h in horas_grupo.items():
        if h > capacidad_grupo:
            err(
                "OFERTA_ACADEMICA",
                f"El grupo {g} pide {h} h semanales y el calendario solo tiene {capacidad_grupo} h "
                f"({n_dias} días × {h1 - h0} h).",
            )

    # 3) Demanda por materia frente a la capacidad de sus profesores (condición necesaria).
    demanda_materia: Counter = Counter()
    for o in datos.ofertas:
        demanda_materia[o.materia] += o.horas_semanales
    for mid, demanda in demanda_materia.items():
        m = mat.get(mid)
        if m is None:
            continue
        profs = [p for p in activos.values() if mid in p.materias]
        if not profs:
            continue  # ya reportado en (1)
        capacidad = 0
        for p in profs:
            c = len(disp[p.id])
            if p.horas_maximas is not None:
                c = min(c, p.horas_maximas)
            capacidad += c
        if demanda > capacidad:
            err(
                "OFERTA_ACADEMICA",
                f"La materia «{m.nombre}» necesita {demanda} h semanales y sus profesores en conjunto solo "
                f"pueden ofrecer {capacidad} h (por disponibilidad y horas máximas).",
            )

    # 4) Profesores con mínimos imposibles de alcanzar.
    demanda_total = sum(o.horas_semanales for o in datos.ofertas)
    suma_minimos = 0
    for p in activos.values():
        if not p.horas_minimas:
            continue
        suma_minimos += p.horas_minimas
        if p.horas_minimas > len(disp[p.id]):
            err(
                "PROFESORES",
                f"{_nombre_prof(datos, p.id)} debe dar al menos {p.horas_minimas} h pero solo tiene "
                f"{len(disp[p.id])} h disponibles.",
            )
        horas_de_sus_materias = sum(o.horas_semanales for o in datos.ofertas if o.materia in p.materias)
        if p.horas_minimas > horas_de_sus_materias:
            err(
                "PROFESORES",
                f"{_nombre_prof(datos, p.id)} debe dar al menos {p.horas_minimas} h, pero las materias que "
                f"puede impartir suman solo {horas_de_sus_materias} h en la oferta.",
            )
    if suma_minimos > demanda_total:
        err(
            "PROFESORES",
            f"La suma de horas mínimas de los profesores ({suma_minimos} h) supera las horas ofertadas ({demanda_total} h).",
        )

    # 5) Profesores obligatorios: carga forzada frente a su capacidad.
    forzado: dict[str, int] = defaultdict(int)
    for o in datos.ofertas:
        if o.profesor_obligatorio:
            forzado[o.profesor_obligatorio] += o.horas_semanales
    for pid, h in forzado.items():
        p = activos.get(pid)
        if p is None:
            continue
        cap = len(disp[pid])
        if p.horas_maximas is not None:
            cap = min(cap, p.horas_maximas)
        if h > cap:
            err(
                "OFERTA_ACADEMICA",
                f"{_nombre_prof(datos, pid)} está marcado como obligatorio para {h} h semanales, pero solo puede "
                f"dar {cap} h (por disponibilidad y horas máximas).",
            )
    return out


FAMILIAS = {
    "limites_horas": "los límites de horas mínimas y máximas de los profesores",
    "una_profesor_por_oferta": "la regla de que una oferta la imparta un solo profesor",
    "profesor_obligatorio": "los profesores marcados como obligatorios",
    "dias_permitidos": "los días permitidos de las ofertas",
    "disponibilidad": "la disponibilidad de los profesores",
    "misma_materia": "la regla de no repetir una materia el mismo día",
}


def _familias_aplicables(datos: Datos) -> list[str]:
    fams = []
    if any(p.horas_maximas is not None or p.horas_minimas for p in datos.profesores if p.activo):
        fams.append("limites_horas")
    if any(o.horas_semanales > 0 for o in datos.ofertas):
        fams.append("una_profesor_por_oferta")
    if any(o.profesor_obligatorio for o in datos.ofertas):
        fams.append("profesor_obligatorio")
    if any(o.dias_permitidos for o in datos.ofertas):
        fams.append("dias_permitidos")
    fams.append("disponibilidad")
    if datos.config.misma_materia_mismo_dia == "obligatorio":
        fams.append("misma_materia")
    return fams


def diagnosticar_inviabilidad(
    datos: Datos, sesiones: list[Sesion], disp: dict, segundos_por_prueba: float = 4.0
) -> list[str]:
    """Tras INFEASIBLE: prueba relajar cada familia de restricciones por separado.

    Devuelve recomendaciones en lenguaje claro. Una prueba que agota el tiempo se
    reporta como inconclusa, nunca como «imposible».
    """
    mensajes: list[str] = []
    factibles: list[str] = []
    inconclusas: list[str] = []
    for fam in _familias_aplicables(datos):
        r = optimizer.resolver(
            datos, sesiones, disp, relajar={fam}, limite=segundos_por_prueba, optimizar=False
        )
        if r.estado in ("OPTIMAL", "FEASIBLE"):
            factibles.append(fam)
        elif r.estado == "UNKNOWN":
            inconclusas.append(fam)
    for fam in factibles:
        mensajes.append(
            f"Si se dejara de exigir {FAMILIAS[fam]}, sí existiría un horario. Revisa esos datos: "
            "es el primer lugar donde conviene ajustar."
        )
    for fam in inconclusas:
        mensajes.append(f"No se pudo comprobar, por falta de tiempo, qué pasa al relajar {FAMILIAS[fam]}.")
    if not factibles:
        mensajes.append(
            "Ninguna de las reglas revisadas, por sí sola, explica el conflicto. Suele deberse a la combinación de "
            "varias: pocas franjas libres en común entre profesores y grupos, o demasiadas horas para los "
            "profesores disponibles. Prueba ampliando la disponibilidad de algún profesor o quitando una oferta."
        )
    mensajes.append(
        "Estas pistas no identifican una causa única: indican qué reglas, al relajarse, hacen posible un horario."
    )
    return mensajes
