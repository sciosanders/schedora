"""Orquesta el flujo completo sin depender de Gradio.

    revisar(ruta)  -> Revision   (leer, validar, construir sesiones, verificaciones previas)
    generar(rev)   -> Salida     (resolver, verificar de forma independiente, métricas)

La interfaz y las pruebas llaman a estas dos funciones.
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field

from . import optimizer
from .availability import calcular_disponibilidad
from .diagnostics import diagnosticar_inviabilidad, verificaciones_previas
from .excel_reader import leer_excel
from .metrics import calcular_metricas
from .models import Asignacion, Datos, ErrorArchivo, Problema, Sesion
from .schedule_validator import validar_horario
from .session_builder import construir_sesiones
from .validator import validar_datos

log = logging.getLogger("schedora")

MAX_SEGUNDOS = int(os.environ.get("SCHEDORA_MAX_SEGUNDOS", "60"))
_SEMAFORO = threading.BoundedSemaphore(int(os.environ.get("SCHEDORA_MAX_SIMULTANEAS", "2")))


@dataclass
class Revision:
    datos: Datos
    problemas: list[Problema]
    sesiones: list[Sesion] = field(default_factory=list)
    disp: dict = field(default_factory=dict)

    @property
    def errores(self) -> list[Problema]:
        return [p for p in self.problemas if p.es_error]

    @property
    def advertencias(self) -> list[Problema]:
        return [p for p in self.problemas if not p.es_error]

    @property
    def ok(self) -> bool:
        return not self.errores

    @property
    def resumen(self) -> dict:
        d = self.datos
        return {
            "profesores": sum(1 for p in d.profesores if p.activo),
            "materias": len(d.materias),
            "grupos": len(d.grupos),
            "sesiones": len(self.sesiones),
            "horas": sum(s.duracion for s in self.sesiones),
            "calendario": f"{d.config.hora_inicio:02d}:00–{d.config.hora_fin:02d}:00, {len(d.config.dias)} días",
        }


@dataclass
class Salida:
    estado: str  # LISTO | SIN_SOLUCION | INCONCLUSO | ENTRADA_INVALIDA | NO_VERIFICADO | ERROR
    estado_motor: str  # OPTIMAL | FEASIBLE | INFEASIBLE | UNKNOWN | MODEL_INVALID | -
    titulo: str
    mensaje: str
    revision: Revision | None = None
    asignaciones: list[Asignacion] = field(default_factory=list)
    metricas: dict = field(default_factory=dict)
    objetivo: float | None = None
    segundos: float = 0.0
    avisos: list[str] = field(default_factory=list)
    sugerencias: list[str] = field(default_factory=list)

    @property
    def exitoso(self) -> bool:
        return self.estado == "LISTO"


def revisar(ruta: str) -> Revision:
    """Lee y valida el archivo. Nunca lanza por datos malos: devuelve problemas."""
    try:
        datos, problemas = leer_excel(ruta)
    except ErrorArchivo as e:
        return Revision(Datos(), [Problema("error", "", None, str(e))])
    rev = Revision(datos, problemas)
    if not rev.ok:
        return rev
    rev.problemas += validar_datos(datos)
    if not rev.ok:
        return rev
    rev.sesiones, extra = construir_sesiones(datos)
    rev.problemas += extra
    if not rev.ok:
        return rev
    rev.disp = calcular_disponibilidad(datos)
    rev.problemas += verificaciones_previas(datos, rev.sesiones, rev.disp)
    return rev


def generar(rev: Revision, limite_segundos: int | None = None) -> Salida:
    if not rev.ok:
        return Salida(
            "ENTRADA_INVALIDA",
            "-",
            "Hay que corregir el archivo antes de generar",
            "Encontramos datos que impiden armar el horario. Revisa la lista, corrígelos en tu Excel y vuelve a subirlo.",
            revision=rev,
        )
    datos = rev.datos
    limite = min(limite_segundos or datos.config.limite_busqueda_segundos, MAX_SEGUNDOS)
    try:
        with _SEMAFORO:
            r = optimizer.resolver(datos, rev.sesiones, rev.disp, limite=limite)
    except Exception:
        log.exception("Fallo interno del motor")  # sin datos personales: solo trazas técnicas
        return Salida(
            "ERROR",
            "-",
            "Algo salió mal de nuestro lado",
            "No pudimos completar la generación. Inténtalo de nuevo en un momento; si se repite, avísanos.",
            revision=rev,
        )

    log.info("Resultado motor=%s sesiones=%d segundos=%.1f", r.estado, len(rev.sesiones), r.segundos)

    if r.estado in ("OPTIMAL", "FEASIBLE"):
        errores = validar_horario(datos, rev.sesiones, r.asignaciones, rev.disp)
        if errores:
            log.error("El horario del motor no pasó la verificación independiente (%d violaciones)", len(errores))
            return Salida(
                "NO_VERIFICADO",
                r.estado,
                "No pudimos verificar el resultado",
                "Por seguridad no lo mostramos como horario válido. Inténtalo de nuevo; si se repite, avísanos.",
                revision=rev,
                segundos=r.segundos,
            )
        metricas = calcular_metricas(datos, r.asignaciones)
        if r.estado == "OPTIMAL":
            msg = "Encontramos el mejor horario posible con tus datos y reglas."
        else:
            msg = (
                "Encontramos un horario válido. No alcanzamos a demostrar que sea el mejor posible en el tiempo "
                "disponible; si quieres, vuelve a generar con más tiempo."
            )
        return Salida(
            "LISTO",
            r.estado,
            "Tu horario está listo",
            msg,
            revision=rev,
            asignaciones=r.asignaciones,
            metricas=metricas,
            objetivo=r.objetivo,
            segundos=r.segundos,
            avisos=r.mensajes,
        )

    if r.estado == "INFEASIBLE":
        try:
            pistas = diagnosticar_inviabilidad(datos, rev.sesiones, rev.disp)
        except Exception:
            log.exception("Fallo en el diagnóstico de inviabilidad")
            pistas = ["No pudimos completar el análisis de causas. Revisa disponibilidad y horas de los profesores."]
        return Salida(
            "SIN_SOLUCION",
            r.estado,
            "No existe un horario con estas reglas",
            "Comprobamos que las reglas se contradicen entre sí. No es un fallo de la aplicación: hay que ajustar "
            "algún dato. Estas pistas te dicen por dónde empezar.",
            revision=rev,
            segundos=r.segundos,
            sugerencias=pistas,
        )

    if r.estado == "UNKNOWN":
        return Salida(
            "INCONCLUSO",
            r.estado,
            "Todavía no sabemos si es posible",
            "El tiempo de búsqueda terminó sin una respuesta concluyente. Esto NO significa que sea imposible. "
            "Prueba con más tiempo, o simplifica un poco los datos (menos grupos o más disponibilidad).",
            revision=rev,
            segundos=r.segundos,
        )

    log.error("Estado inesperado del motor: %s", r.estado)
    return Salida(
        "ERROR",
        r.estado,
        "Algo salió mal de nuestro lado",
        "El modelo no se pudo construir correctamente. Avísanos para revisarlo.",
        revision=rev,
        segundos=r.segundos,
    )
