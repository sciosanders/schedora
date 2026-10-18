"""Validador independiente del horario.

No importa el optimizador ni comparte código con él: revisa el resultado contra
los datos de entrada. Un horario que no pase estas comprobaciones nunca se
presenta como válido ni se exporta.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from .availability import calcular_disponibilidad
from .models import Asignacion, Datos, Sesion


def validar_horario(
    datos: Datos,
    sesiones: list[Sesion],
    asignaciones: list[Asignacion],
    disp: dict | None = None,
) -> list[str]:
    """Devuelve la lista de violaciones (vacía = horario válido)."""
    errores: list[str] = []
    cfg = datos.config
    disp = disp if disp is not None else calcular_disponibilidad(datos)
    por_id = {s.id: s for s in sesiones}
    ofertas = {o.id: o for o in datos.ofertas}
    profs = {p.id: p for p in datos.profesores}

    # 1) Todas las sesiones, una sola vez, sin sobrantes.
    veces = Counter(a.sesion_id for a in asignaciones)
    for sid in por_id:
        if veces.get(sid, 0) == 0:
            errores.append(f"Sesión {sid} sin programar.")
        elif veces[sid] > 1:
            errores.append(f"Sesión {sid} programada {veces[sid]} veces.")
    for sid in veces:
        if sid not in por_id:
            errores.append(f"Sesión inexistente en el horario: {sid}.")

    ocup_prof: dict[tuple, int] = defaultdict(int)
    ocup_grupo: dict[tuple, int] = defaultdict(int)
    horas_prof: dict[str, int] = defaultdict(int)
    profs_de_oferta: dict[str, set] = defaultdict(set)
    horas_oferta: dict[str, int] = defaultdict(int)
    dias_de_oferta: dict[tuple, int] = defaultdict(int)

    for a in asignaciones:
        s = por_id.get(a.sesion_id)
        if s is None:
            continue
        o = ofertas.get(s.oferta_id)
        # 2) Duración y coherencia con la sesión.
        if a.duracion != s.duracion:
            errores.append(f"{a.sesion_id}: duración {a.duracion} h, se esperaban {s.duracion} h.")
        if (a.grupo, a.materia, a.oferta_id) != (s.grupo, s.materia, s.oferta_id):
            errores.append(f"{a.sesion_id}: grupo/materia/oferta no coinciden con la sesión solicitada.")
        # 10) Calendario.
        if a.dia not in cfg.dias:
            errores.append(f"{a.sesion_id}: día «{a.dia}» fuera del calendario.")
            continue
        d = cfg.dias.index(a.dia)
        if a.inicio < cfg.hora_inicio or a.inicio + s.duracion > cfg.hora_fin:
            errores.append(
                f"{a.sesion_id}: {a.inicio:02d}:00–{a.inicio + s.duracion:02d}:00 sale del horario "
                f"{cfg.hora_inicio:02d}:00–{cfg.hora_fin:02d}:00."
            )
        # 3) Profesor existente, activo y capacitado.
        p = profs.get(a.profesor_id)
        if p is None:
            errores.append(f"{a.sesion_id}: el profesor «{a.profesor_id}» no existe.")
            continue
        if not p.activo:
            errores.append(f"{a.sesion_id}: el profesor «{p.id}» está inactivo.")
        if s.materia not in p.materias:
            errores.append(f"{a.sesion_id}: el profesor «{p.id}» no está capacitado para «{s.materia}».")
        if o is not None:
            if o.profesor_obligatorio and o.profesor_obligatorio != p.id:
                errores.append(f"{a.sesion_id}: la oferta exige al profesor «{o.profesor_obligatorio}».")
            if o.dias_permitidos and a.dia not in o.dias_permitidos:
                errores.append(f"{a.sesion_id}: el día «{a.dia}» no está permitido para la oferta.")
        # 7) Disponibilidad durante toda la sesión.
        for h in range(a.inicio, a.inicio + s.duracion):
            if (d, h) not in disp.get(p.id, set()):
                errores.append(f"{a.sesion_id}: «{p.id}» no está disponible el {a.dia} a las {h:02d}:00.")
            ocup_prof[(p.id, d, h)] += 1
            ocup_grupo[(s.grupo, d, h)] += 1
        horas_prof[p.id] += s.duracion
        profs_de_oferta[s.oferta_id].add(p.id)
        horas_oferta[s.oferta_id] += s.duracion
        dias_de_oferta[(s.oferta_id, d)] += 1

    # 4, 5) Sin empalmes.
    for (pid, d, h), n in ocup_prof.items():
        if n > 1:
            errores.append(f"Empalme docente: «{pid}» tiene {n} clases el {cfg.dias[d]} a las {h:02d}:00.")
    for (g, d, h), n in ocup_grupo.items():
        if n > 1:
            errores.append(f"Empalme de grupo: «{g}» tiene {n} clases el {cfg.dias[d]} a las {h:02d}:00.")

    # 8) Horas mínimas y máximas.
    for p in datos.profesores:
        if not p.activo:
            continue
        h = horas_prof.get(p.id, 0)
        if p.horas_maximas is not None and h > p.horas_maximas:
            errores.append(f"«{p.id}» tiene {h} h y su máximo es {p.horas_maximas} h.")
        if p.horas_minimas is not None and h < p.horas_minimas:
            errores.append(f"«{p.id}» tiene {h} h y su mínimo es {p.horas_minimas} h.")

    # 11) Horas semanales cumplidas exactamente; un profesor por oferta.
    for o in datos.ofertas:
        if horas_oferta.get(o.id, 0) != o.horas_semanales:
            errores.append(f"Oferta {o.id}: {horas_oferta.get(o.id, 0)} h programadas de {o.horas_semanales} h pedidas.")
        if len(profs_de_oferta.get(o.id, ())) > 1:
            errores.append(f"Oferta {o.id}: la imparten varios profesores ({', '.join(sorted(profs_de_oferta[o.id]))}).")

    # Regla opcional: misma materia el mismo día, solo si es obligatoria.
    if cfg.misma_materia_mismo_dia == "obligatorio":
        for (oid, d), n in dias_de_oferta.items():
            if n > 1:
                errores.append(f"Oferta {oid}: {n} sesiones el {cfg.dias[d]} (la regla es obligatoria).")
    return errores
