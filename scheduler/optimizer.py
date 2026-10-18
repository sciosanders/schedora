"""Motor de horarios con OR-Tools CP-SAT.

Variable principal (plan, sección 10):
    x[s, p, d, t] = 1  si la sesión s la imparte el profesor p el día d a partir de la hora t.
Solo se crean las combinaciones compatibles con la duración, el calendario, la
disponibilidad y las competencias del profesor.

Restricciones obligatorias: ver `_construir`. Preferencias: huecos de profesores
(ponderados por carga objetivo), huecos de grupos, días trabajados por profesor y
repetición de una materia el mismo día.

`relajar` permite quitar una familia de restricciones; el módulo de diagnósticos lo
usa para averiguar qué familia, al relajarse, vuelve factible el problema.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from .availability import calcular_disponibilidad, inicios_validos
from .models import Asignacion, Datos, Sesion

try:  # OR-Tools es obligatorio en producción; el resto del paquete funciona sin él.
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover
    cp_model = None

ESTADOS = ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN", "MODEL_INVALID")


@dataclass
class ResultadoMotor:
    estado: str
    asignaciones: list[Asignacion] = field(default_factory=list)
    objetivo: float | None = None
    segundos: float = 0.0
    mensajes: list[str] = field(default_factory=list)


def ortools_disponible() -> bool:
    return cp_model is not None


def pesos_docentes(datos: Datos) -> tuple[dict[str, int], list[str]]:
    """peso(p) = peso_continuidad // (1 + horas_objetivo(p)), siempre entero >= 1.

    Si un profesor no tiene horas_objetivo se usa una carga de referencia calculada
    con los datos (horas ofertadas / profesores con materias ofertadas) y se avisa.
    """
    cfg = datos.config
    materias_ofertadas = {o.materia for o in datos.ofertas}
    activos = [p for p in datos.profesores if p.activo]
    con_materias = [p for p in activos if p.materias & materias_ofertadas]
    demanda = sum(o.horas_semanales for o in datos.ofertas)
    referencia = demanda / max(1, len(con_materias))
    pesos: dict[str, int] = {}
    sin_objetivo: list[str] = []
    for p in activos:
        if p.horas_objetivo is not None:
            h = p.horas_objetivo
        else:
            h = referencia
            sin_objetivo.append(p.id)
        pesos[p.id] = max(1, cfg.peso_continuidad // (1 + int(round(h))))
    mensajes: list[str] = []
    if sin_objetivo:
        mensajes.append(
            f"{len(sin_objetivo)} profesor(es) no tienen horas_objetivo_semana; para priorizar la continuidad "
            f"se usó una carga de referencia de {referencia:.1f} h (horas ofertadas ÷ profesores con materias "
            "ofertadas). Puedes fijar la carga de cada profesor en la hoja PROFESORES."
        )
    return pesos, mensajes


def _candidatos(o, activos, materias_ids, relajar) -> list[str]:
    if o.profesor_obligatorio and "profesor_obligatorio" not in relajar:
        p = activos.get(o.profesor_obligatorio)
        return [p.id] if p is not None and o.materia in p.materias else []
    return [pid for pid, p in activos.items() if o.materia in p.materias]


def _agregar_huecos(model, cubre, coef_hueco, coef_uso_dia, h0, h1, objetivo, prefijo):
    """Penaliza huecos internos (y, opcionalmente, días usados) por entidad y día.

    cubre: {(entidad, dia, hora): [variables que ocupan ese bloque]}
    Cada entidad tiene como máximo una clase por bloque, así que la suma es 0/1.
    """
    por_ent_dia: dict[tuple, dict[int, list]] = defaultdict(dict)
    for (ent, d, h), lst in cubre.items():
        por_ent_dia[(ent, d)][h] = lst
    for (ent, d), horas in por_ent_dia.items():
        ch = coef_hueco(ent)
        cu = coef_uso_dia(ent)
        if ch <= 0 and cu <= 0:
            continue
        ocupado = {}
        for h, lst in horas.items():
            b = model.NewBoolVar(f"{prefijo}_o_{ent}_{d}_{h}")
            model.Add(b == sum(lst))
            ocupado[h] = b
        if ch > 0 and len(ocupado) >= 2:
            primero = model.NewIntVar(h0, h1 - 1, f"{prefijo}_ini_{ent}_{d}")
            ultimo = model.NewIntVar(h0, h1 - 1, f"{prefijo}_fin_{ent}_{d}")
            for h, b in ocupado.items():
                model.Add(primero <= h).OnlyEnforceIf(b)
                model.Add(ultimo >= h).OnlyEnforceIf(b)
            hueco = model.NewIntVar(0, h1 - h0, f"{prefijo}_hueco_{ent}_{d}")
            model.Add(hueco >= ultimo - primero + 1 - sum(ocupado.values()))
            objetivo.append((ch, hueco))
        if cu > 0:
            usado = model.NewBoolVar(f"{prefijo}_dia_{ent}_{d}")
            for b in ocupado.values():
                model.AddImplication(b, usado)
            objetivo.append((cu, usado))


def _construir(datos: Datos, sesiones: list[Sesion], disp, relajar: frozenset, con_objetivo: bool):
    cfg = datos.config
    model = cp_model.CpModel()
    n_dias = len(cfg.dias)
    h0, h1 = cfg.hora_inicio, cfg.hora_fin
    activos = {p.id: p for p in datos.profesores if p.activo}
    ofertas = {o.id: o for o in datos.ofertas}
    calendario = {(i, h) for i in range(n_dias) for h in range(h0, h1)}

    x: dict[tuple, object] = {}
    por_sesion: dict[str, list] = defaultdict(list)
    por_sesion_prof: dict[tuple, list] = defaultdict(list)
    cubre_prof: dict[tuple, list] = defaultdict(list)
    cubre_grupo: dict[tuple, list] = defaultdict(list)
    horas_prof: dict[str, list] = defaultdict(list)
    por_oferta_dia: dict[tuple, list] = defaultdict(list)
    sesiones_de_oferta: dict[str, list[str]] = defaultdict(list)

    for s in sesiones:
        o = ofertas[s.oferta_id]
        sesiones_de_oferta[o.id].append(s.id)
        if o.dias_permitidos and "dias_permitidos" not in relajar:
            dias_ok = [i for i, d in enumerate(cfg.dias) if d in o.dias_permitidos]
        else:
            dias_ok = list(range(n_dias))
        for pid in _candidatos(o, activos, None, relajar):
            bloques = calendario if "disponibilidad" in relajar else disp[pid]
            for d in dias_ok:
                for t in inicios_validos(bloques, d, s.duracion, cfg):
                    v = model.NewBoolVar(f"x_{s.id}_{pid}_{d}_{t}")
                    x[(s.id, pid, d, t)] = v
                    por_sesion[s.id].append(v)
                    por_sesion_prof[(s.id, pid)].append(v)
                    horas_prof[pid].append((s.duracion, v))
                    por_oferta_dia[(o.id, d)].append(v)
                    for k in range(s.duracion):
                        cubre_prof[(pid, d, t + k)].append(v)
                        cubre_grupo[(s.grupo, d, t + k)].append(v)

    # C1: cada sesión exactamente una vez (si no hay ninguna opción, el modelo es infactible).
    for s in sesiones:
        opciones = por_sesion.get(s.id, [])
        if opciones:
            model.AddExactlyOne(opciones)
        else:
            z = model.NewBoolVar(f"sin_opciones_{s.id}")
            model.Add(z == 0)
            model.Add(z == 1)

    # C4, C5: sin empalmes de profesores ni de grupos.
    for lst in cubre_prof.values():
        if len(lst) > 1:
            model.AddAtMostOne(lst)
    for lst in cubre_grupo.values():
        if len(lst) > 1:
            model.AddAtMostOne(lst)

    # C12: un solo profesor por oferta.
    if "una_profesor_por_oferta" not in relajar:
        for oid, sids in sesiones_de_oferta.items():
            if len(sids) < 2:
                continue
            cand = _candidatos(ofertas[oid], activos, None, relajar)
            if not cand:
                continue
            y = {pid: model.NewBoolVar(f"y_{oid}_{pid}") for pid in cand}
            model.AddExactlyOne(list(y.values()))
            for sid in sids:
                for pid in cand:
                    lst = por_sesion_prof.get((sid, pid), [])
                    if lst:
                        model.Add(sum(lst) == y[pid])
                    else:
                        model.Add(y[pid] == 0)

    # C8: límites de horas mínimas y máximas.
    if "limites_horas" not in relajar:
        for pid, p in activos.items():
            terminos = horas_prof.get(pid, [])
            if terminos:
                total = sum(dur * v for dur, v in terminos)
                if p.horas_maximas is not None:
                    model.Add(total <= p.horas_maximas)
                if p.horas_minimas is not None and p.horas_minimas > 0:
                    model.Add(total >= p.horas_minimas)
            elif p.horas_minimas is not None and p.horas_minimas > 0:
                z = model.NewBoolVar(f"sin_horas_{pid}")
                model.Add(z == 0)
                model.Add(z == 1)

    objetivo: list[tuple[int, object]] = []

    # Misma materia el mismo día: obligatorio, preferencia o libre.
    modo = cfg.misma_materia_mismo_dia
    if modo != "permitir" and "misma_materia" not in relajar:
        for oid, sids in sesiones_de_oferta.items():
            if len(sids) < 2:
                continue
            for d in range(n_dias):
                vs = por_oferta_dia.get((oid, d), [])
                if len(vs) < 2:
                    continue
                if modo == "obligatorio":
                    model.Add(sum(vs) <= 1)
                elif con_objetivo and cfg.peso_misma_materia_dia > 0:
                    exceso = model.NewIntVar(0, len(sids), f"exceso_{oid}_{d}")
                    model.Add(exceso >= sum(vs) - 1)
                    objetivo.append((cfg.peso_misma_materia_dia, exceso))

    mensajes: list[str] = []
    if con_objetivo:
        pesos, mensajes = pesos_docentes(datos)
        _agregar_huecos(
            model,
            cubre_prof,
            coef_hueco=lambda pid: pesos.get(pid, 1),
            coef_uso_dia=lambda pid: (pesos.get(pid, 1) * cfg.peso_dias_docente) // 100,
            h0=h0,
            h1=h1,
            objetivo=objetivo,
            prefijo="p",
        )
        _agregar_huecos(
            model,
            cubre_grupo,
            coef_hueco=lambda g: cfg.peso_grupos,
            coef_uso_dia=lambda g: 0,
            h0=h0,
            h1=h1,
            objetivo=objetivo,
            prefijo="g",
        )
        if objetivo:
            model.Minimize(sum(c * v for c, v in objetivo))
    return model, x, mensajes, bool(objetivo)


def resolver(
    datos: Datos,
    sesiones: list[Sesion],
    disp: dict | None = None,
    relajar: frozenset | set = frozenset(),
    limite: float | None = None,
    optimizar: bool = True,
) -> ResultadoMotor:
    """Construye y resuelve el modelo. `estado` es el nombre del estado de CP-SAT."""
    if cp_model is None:
        raise RuntimeError("OR-Tools no está instalado (pip install ortools).")
    cfg = datos.config
    disp = disp if disp is not None else calcular_disponibilidad(datos)
    relajar = frozenset(relajar)
    inicio = time.monotonic()
    model, x, mensajes, hay_objetivo = _construir(datos, sesiones, disp, relajar, optimizar)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(limite if limite is not None else cfg.limite_busqueda_segundos)
    hilos = 1 if cfg.semilla_busqueda is not None else max(1, int(cfg.num_workers))
    try:
        solver.parameters.num_workers = hilos
    except AttributeError:  # versiones antiguas de OR-Tools
        solver.parameters.num_search_workers = hilos
    if cfg.semilla_busqueda is not None:
        solver.parameters.random_seed = int(cfg.semilla_busqueda)

    status = solver.Solve(model)
    estado = solver.StatusName(status)
    resultado = ResultadoMotor(estado=estado, segundos=time.monotonic() - inicio, mensajes=mensajes)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        sesion_por_id = {s.id: s for s in sesiones}
        for (sid, pid, d, t), v in x.items():
            if solver.Value(v):
                s = sesion_por_id[sid]
                resultado.asignaciones.append(
                    Asignacion(
                        sesion_id=sid,
                        oferta_id=s.oferta_id,
                        grupo=s.grupo,
                        materia=s.materia,
                        profesor_id=pid,
                        dia=cfg.dias[d],
                        inicio=t,
                        duracion=s.duracion,
                    )
                )
        resultado.asignaciones.sort(key=lambda a: (cfg.dias.index(a.dia), a.inicio, a.grupo))
        if hay_objetivo:
            resultado.objetivo = solver.ObjectiveValue()
    return resultado
