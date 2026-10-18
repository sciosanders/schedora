"""Coordina las acciones de la interfaz: acceso, revisión, generación y vistas.

Cada callback vuelve a verificar el acceso en el servidor (el código vive en gr.State,
del lado del servidor), de modo que un acceso vencido o desactivado deja de funcionar
aunque la página siga abierta. No se muestran trazas técnicas a la persona usuaria.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time

import pandas as pd

try:  # los callbacks se pueden probar sin Gradio instalado
    import gradio as gr

    actualizar = gr.update
except ImportError:  # pragma: no cover
    def actualizar(**kw):
        return dict(kw)

from acceso.tokens import acceso_abierto, verificar_codigo
from scheduler import exporter, service
from scheduler.vistas import cuadricula, entidades
from . import render

log = logging.getLogger("schedora.ui")

PREFIJO_TMP = "schedora_"
EDAD_MAXIMA_TMP = 3600  # segundos


# ------------------------------------------------------------------ temporales
def _limpiar_temporales() -> None:
    """Borra carpetas temporales de salida con más de una hora."""
    base = tempfile.gettempdir()
    ahora = time.time()
    try:
        for nombre in os.listdir(base):
            ruta = os.path.join(base, nombre)
            if nombre.startswith(PREFIJO_TMP) and os.path.isdir(ruta) and ahora - os.path.getmtime(ruta) > EDAD_MAXIMA_TMP:
                shutil.rmtree(ruta, ignore_errors=True)
    except OSError:
        pass


def _ruta_salida(nombre: str) -> str:
    """Carpeta propia por solicitud: evita colisiones entre usuarios concurrentes."""
    carpeta = tempfile.mkdtemp(prefix=PREFIJO_TMP)
    return os.path.join(carpeta, nombre)


def _borrar(ruta: str | None) -> None:
    """Elimina el archivo subido una vez leído (no se conservan los originales)."""
    try:
        if ruta and os.path.isfile(ruta):
            os.remove(ruta)
    except OSError:
        pass


# ---------------------------------------------------------------------- acceso
def _comprobar_acceso(token: str | None):
    """Devuelve (valido, resultado). En modo abierto (solo desarrollo) siempre es válido."""
    if acceso_abierto():
        return True, None
    if not token:
        return False, None
    r = verificar_codigo(token)
    return r.valido, r


def entrar(codigo: str):
    """Pantalla de acceso -> (token, compuerta, app, mensaje, banner_acceso)."""
    if acceso_abierto():
        return ("abierto", actualizar(visible=False), actualizar(visible=True), "", render.acceso_html("", True))
    r = verificar_codigo(codigo)
    if not r.valido:
        time.sleep(1.0)  # frena adivinanzas de códigos sin molestar a quien se equivocó una vez
        return (None, actualizar(visible=True), actualizar(visible=False), render.banner("warn", r.mensaje), "")
    return (codigo, actualizar(visible=False), actualizar(visible=True), "", render.acceso_html(r.vence_texto()))


def _acceso_vencido_html(token) -> str:
    ok, r = _comprobar_acceso(token)
    mensaje = r.mensaje if r is not None else "Vuelve a escribir tu código de acceso."
    return render.banner("warn", "Tu acceso ya no está activo", mensaje + " Recarga la página para entrar de nuevo.")


# -------------------------------------------------------------------- revisión
def revisar_archivo(archivo, token):
    """-> (revision, html, boton_generar, boton_diagnostico, grupo_resultados)"""
    ok, _ = _comprobar_acceso(token)
    if not ok:
        return (None, _acceso_vencido_html(token), actualizar(interactive=False), actualizar(visible=False), actualizar(visible=False))
    if not archivo:
        return (
            None,
            render.banner("info", "Primero elige tu archivo", "Súbelo en el recuadro de arriba (formato .xlsx) y vuelve a pulsar «Revisar archivo»."),
            actualizar(interactive=False),
            actualizar(visible=False),
            actualizar(visible=False),
        )
    ruta = archivo if isinstance(archivo, str) else getattr(archivo, "name", str(archivo))
    try:
        rev = service.revisar(ruta)
    except Exception:
        log.exception("Fallo al revisar el archivo")
        return (
            None,
            render.banner("err", "No pudimos leer el archivo", "Verifica que sea un .xlsx sin contraseña e inténtalo de nuevo."),
            actualizar(interactive=False),
            actualizar(visible=False),
            actualizar(visible=False),
        )
    finally:
        _borrar(ruta)
    _limpiar_temporales()
    diag = actualizar(visible=False)
    if rev.problemas:
        try:
            diag = actualizar(value=exporter.exportar_diagnostico(rev, None, _ruta_salida("diagnostico_schedora.xlsx")), visible=True)
        except Exception:
            log.exception("No se pudo crear el diagnóstico")
    return (rev, render.revision_html(rev), actualizar(interactive=rev.ok), diag, actualizar(visible=False))


# ------------------------------------------------------------------ generación
def _tabla(df_filas, encabezados) -> pd.DataFrame:
    return pd.DataFrame(df_filas, columns=encabezados)


def _vista(salida: service.Salida, tipo: str, entidad: str | None):
    if salida is None or not salida.exitoso or not entidad:
        return pd.DataFrame()
    encabezados, filas, _ = cuadricula(salida.revision.datos, salida.asignaciones, tipo, entidad)
    return _tabla(filas, encabezados)


def _tabla_carga(salida: service.Salida) -> pd.DataFrame:
    filas = [
        [
            f["nombre"],
            "—" if f["horas_objetivo"] is None else f["horas_objetivo"],
            f["horas"],
            f["dias"],
            f["huecos"],
        ]
        for f in salida.metricas.get("profesores", [])
    ]
    return _tabla(filas, ["Profesor", "Horas objetivo", "Horas asignadas", "Días con clase", "Huecos (h)"])


def generar_horario(rev, segundos, token):
    """-> (salida, html, grupo_resultados, radio, dropdown, tabla, tabla_carga, boton_excel, boton_diag)"""
    ok, _ = _comprobar_acceso(token)
    vacio = pd.DataFrame()
    if not ok:
        return (None, _acceso_vencido_html(token), actualizar(visible=False), actualizar(), actualizar(), vacio, vacio, actualizar(visible=False), actualizar(visible=False))
    if rev is None:
        return (
            None,
            render.banner("info", "Primero revisa tu archivo", "Sube tu Excel y pulsa «Revisar archivo»; después podrás generar."),
            actualizar(visible=False),
            actualizar(),
            actualizar(),
            vacio,
            vacio,
            actualizar(visible=False),
            actualizar(visible=False),
        )
    salida = service.generar(rev, int(segundos) if segundos else None)
    html_estado = render.salida_html(salida)
    # Reporte de diagnóstico: siempre que algo no salió bien o hay avisos que conviene conservar.
    diag = actualizar(visible=False)
    if not salida.exitoso or rev.advertencias or salida.avisos:
        try:
            diag = actualizar(value=exporter.exportar_diagnostico(rev, salida, _ruta_salida("diagnostico_schedora.xlsx")), visible=True)
        except Exception:
            log.exception("No se pudo crear el diagnóstico")
    if not salida.exitoso:
        # Sin horario válido no se muestra la tarjeta de resultados.
        return (salida, html_estado, actualizar(visible=False), actualizar(visible=False), actualizar(visible=False), vacio, vacio, actualizar(visible=False), diag)
    # Solo un horario verificado llega a exportarse.
    excel = actualizar(visible=False)
    try:
        excel = actualizar(value=exporter.exportar_horario(salida, _ruta_salida("horario_schedora.xlsx")), visible=True)
    except Exception:
        log.exception("No se pudo exportar el horario")
    opciones = entidades(rev.datos, salida.asignaciones, "grupo")
    primero = opciones[0][1] if opciones else None
    return (
        salida,
        html_estado,
        actualizar(visible=True),
        actualizar(visible=True, value="grupo"),
        actualizar(visible=True, choices=opciones, value=primero),
        _vista(salida, "grupo", primero),
        _tabla_carga(salida),
        excel,
        diag,
    )


def cambiar_tipo(salida, tipo):
    """Al cambiar entre grupo y profesor: renueva el selector y la tabla."""
    if salida is None or not salida.exitoso:
        return actualizar(), pd.DataFrame()
    opciones = entidades(salida.revision.datos, salida.asignaciones, tipo)
    primero = opciones[0][1] if opciones else None
    return actualizar(choices=opciones, value=primero), _vista(salida, tipo, primero)


def cambiar_entidad(salida, tipo, entidad):
    return _vista(salida, tipo, entidad)


def reiniciar():
    """-> (archivo, revision, salida, html_revision, html_estado, boton_generar, grupo_resultados, diag)"""
    return (None, None, None, "", "", actualizar(interactive=False), actualizar(visible=False), actualizar(visible=False))
