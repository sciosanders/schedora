"""Validación de integridad de los datos (antes de construir sesiones ni modelo)."""
from __future__ import annotations

from collections import Counter

from .models import MISMA_MATERIA_MODOS, Datos, Problema


def _duplicados(ids: list[str]) -> set[str]:
    return {k for k, v in Counter(ids).items() if v > 1}


def validar_datos(datos: Datos) -> list[Problema]:
    """Devuelve errores (bloquean) y advertencias (informan)."""
    out: list[Problema] = []
    cfg = datos.config

    def err(hoja, fila, msg):
        out.append(Problema("error", hoja, fila, msg))

    def adv(hoja, fila, msg):
        out.append(Problema("advertencia", hoja, fila, msg))

    # --- configuración -----------------------------------------------------
    if cfg.hora_inicio >= cfg.hora_fin:
        err("CONFIGURACION", None, "hora_inicio debe ser anterior a hora_fin.")
    if not cfg.dias:
        err("CONFIGURACION", None, "Debe haber al menos un día de clases.")
    if cfg.misma_materia_mismo_dia not in MISMA_MATERIA_MODOS:
        err("CONFIGURACION", None, "misma_materia_mismo_dia no es válido.")
    if cfg.limite_busqueda_segundos < 1:
        err("CONFIGURACION", None, "limite_busqueda_segundos debe ser al menos 1.")

    # --- duplicados (V11) --------------------------------------------------
    for d in sorted(_duplicados([p.id for p in datos.profesores])):
        err("PROFESORES", None, f"profesor_id duplicado: «{d}».")
    for d in sorted(_duplicados([m.id for m in datos.materias])):
        err("MATERIAS", None, f"materia_id duplicado: «{d}».")
    for d in sorted(_duplicados([o.id for o in datos.ofertas])):
        err("OFERTA_ACADEMICA", None, f"oferta_id duplicado: «{d}».")

    # --- libro vacío -------------------------------------------------------
    if not any(p.activo for p in datos.profesores):
        err("PROFESORES", None, "No hay profesores activos. Agrega al menos uno en la hoja PROFESORES.")
    if not datos.materias:
        err("MATERIAS", None, "No hay materias. Agrega al menos una en la hoja MATERIAS.")
    if not datos.ofertas:
        err("OFERTA_ACADEMICA", None, "No hay oferta académica. Agrega qué grupos reciben qué materias en la hoja OFERTA_ACADEMICA.")

    prof_ids = {p.id for p in datos.profesores}
    mat = {m.id: m for m in datos.materias}

    # --- materias (V4) -----------------------------------------------------
    for m in datos.materias:
        if m.duracion not in (1, 2):
            err("MATERIAS", None, f"La materia «{m.id}» tiene duracion_sesion={m.duracion}; debe ser 1 o 2 horas.")

    # --- profesores (V6, V9) ----------------------------------------------
    for p in datos.profesores:
        desconocidas = sorted(p.materias - set(mat))
        for mid in desconocidas:
            err("PROFESORES", None, f"El profesor «{p.id}» tiene la materia «{mid}», que no existe en MATERIAS.")
        if p.horas_minimas is not None and p.horas_maximas is not None and p.horas_minimas > p.horas_maximas:
            err("PROFESORES", None, f"El profesor «{p.id}» tiene horas mínimas ({p.horas_minimas}) mayores que las máximas ({p.horas_maximas}).")
        for nombre, v in (("horas_minimas", p.horas_minimas), ("horas_maximas", p.horas_maximas)):
            if v is not None and v < 0:
                err("PROFESORES", None, f"El profesor «{p.id}» tiene {nombre} negativas.")
        if p.horas_objetivo is not None and p.horas_objetivo < 0:
            err("PROFESORES", None, f"El profesor «{p.id}» tiene horas_objetivo negativas.")
        if p.activo and not p.materias:
            adv("PROFESORES", None, f"El profesor «{p.id}» no tiene materias asignadas; no recibirá clases.")
        if (
            p.horas_objetivo is not None
            and p.horas_maximas is not None
            and p.horas_objetivo > p.horas_maximas
        ):
            adv("PROFESORES", None, f"El profesor «{p.id}» tiene horas objetivo mayores que su máximo; se respetará el máximo.")

    # --- ofertas (V1, V2, V3, V5, V12) --------------------------------------
    for o in datos.ofertas:
        if o.materia not in mat:
            err("OFERTA_ACADEMICA", None, f"La oferta «{o.id}» usa la materia «{o.materia}», que no existe en MATERIAS.")
            continue
        if o.horas_semanales <= 0:
            err("OFERTA_ACADEMICA", None, f"La oferta «{o.id}» debe tener horas semanales positivas.")
            continue
        dur = mat[o.materia].duracion
        if dur in (1, 2):
            if o.horas_semanales % dur != 0:
                err(
                    "OFERTA_ACADEMICA",
                    None,
                    f"La oferta «{o.id}» pide {o.horas_semanales} h semanales pero la materia «{o.materia}» "
                    f"se imparte en sesiones de {dur} h: {o.horas_semanales} no es múltiplo de {dur}. "
                    "Corrige las horas o la duración (no se redondea ni se inventan horas).",
                )
            elif o.sesiones_semanales is not None and o.sesiones_semanales * dur != o.horas_semanales:
                err(
                    "OFERTA_ACADEMICA",
                    None,
                    f"La oferta «{o.id}» indica {o.sesiones_semanales} sesiones de {dur} h, que no suman las "
                    f"{o.horas_semanales} h semanales pedidas.",
                )
        if o.profesor_obligatorio is not None:
            p = datos.profesor(o.profesor_obligatorio)
            if o.profesor_obligatorio not in prof_ids:
                err("OFERTA_ACADEMICA", None, f"La oferta «{o.id}» exige al profesor «{o.profesor_obligatorio}», que no existe.")
            elif not p.activo:
                err("OFERTA_ACADEMICA", None, f"La oferta «{o.id}» exige al profesor «{o.profesor_obligatorio}», que está inactivo.")
            elif o.materia not in p.materias:
                err("OFERTA_ACADEMICA", None, f"La oferta «{o.id}» exige al profesor «{o.profesor_obligatorio}», pero él no tiene la materia «{o.materia}».")
        if o.dias_permitidos is not None:
            fuera = [d for d in o.dias_permitidos if d not in cfg.dias]
            if fuera:
                err("OFERTA_ACADEMICA", None, f"La oferta «{o.id}» permite días fuera del calendario: {', '.join(fuera)}.")
            if not o.dias_permitidos:
                err("OFERTA_ACADEMICA", None, f"La oferta «{o.id}» no deja ningún día permitido.")

    # --- disponibilidad (V7, V8, V12) ---------------------------------------
    for f in datos.disponibilidad:
        if f.profesor_id not in prof_ids:
            err("DISPONIBILIDAD", f.fila, f"El profesor «{f.profesor_id}» no existe en PROFESORES.")
        if f.dia not in cfg.dias:
            err("DISPONIBILIDAD", f.fila, f"El día «{f.dia}» no está en el calendario configurado.")
        if f.hora_inicio >= f.hora_fin:
            err("DISPONIBILIDAD", f.fila, f"La hora de inicio ({f.hora_inicio:02d}:00) debe ser anterior a la de fin ({f.hora_fin:02d}:00).")
        elif f.hora_inicio < cfg.hora_inicio or f.hora_fin > cfg.hora_fin:
            adv(
                "DISPONIBILIDAD",
                f.fila,
                f"El intervalo {f.hora_inicio:02d}:00–{f.hora_fin:02d}:00 sale del calendario "
                f"({cfg.hora_inicio:02d}:00–{cfg.hora_fin:02d}:00); solo cuenta la parte dentro del calendario.",
            )

    # Intervalos que se contradicen (DISPONIBLE y NO_DISPONIBLE solapados): se avisa,
    # y prevalece NO_DISPONIBLE (ver availability.py).
    por_prof: dict[str, list] = {}
    for f in datos.disponibilidad:
        if f.hora_inicio < f.hora_fin:
            por_prof.setdefault(f.profesor_id, []).append(f)
    for pid, filas in por_prof.items():
        for a in filas:
            for b in filas:
                if (
                    a.tipo == "DISPONIBLE"
                    and b.tipo == "NO_DISPONIBLE"
                    and a.dia == b.dia
                    and a.hora_inicio < b.hora_fin
                    and b.hora_inicio < a.hora_fin
                ):
                    adv(
                        "DISPONIBILIDAD",
                        b.fila,
                        f"Para «{pid}» el {b.dia} hay un intervalo NO_DISPONIBLE que se cruza con uno DISPONIBLE; "
                        "prevalece NO_DISPONIBLE.",
                    )

    # --- ofertas de un mismo grupo con la misma materia -----------------------
    claves = Counter((o.grupo, o.materia) for o in datos.ofertas)
    for (g, m), n in claves.items():
        if n > 1:
            adv("OFERTA_ACADEMICA", None, f"El grupo «{g}» tiene {n} ofertas de la misma materia «{m}».")

    return out
