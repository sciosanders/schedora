"""Mensajes e indicadores en HTML. Funciones puras: no dependen de Gradio.

Todo texto que viene del archivo del usuario (nombres, ids) se escapa antes de
insertarse en el HTML. El tono es sereno y claro: decir qué pasó y qué hacer.
"""
from __future__ import annotations

import html

from scheduler.service import Revision, Salida

ICONOS = {"ok": "✓", "warn": "!", "err": "×", "info": "i"}


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def banner(clase: str, titulo: str, cuerpo: str = "", extra: str = "") -> str:
    """clase: ok | warn | err | info. El icono y el título evitan depender solo del color."""
    cuerpo_html = f'<p class="sch-b-texto">{esc(cuerpo)}</p>' if cuerpo else ""
    return (
        f'<div class="sch-banner sch-{clase}" role="status">'
        f'<div class="sch-b-icono" aria-hidden="true">{ICONOS.get(clase, "i")}</div>'
        f'<div class="sch-b-cuerpo"><p class="sch-b-titulo">{esc(titulo)}</p>{cuerpo_html}{extra}</div>'
        "</div>"
    )


def _chips(pares: list[tuple[str, object]]) -> str:
    return '<div class="sch-chips">' + "".join(
        f'<span class="sch-chip"><b>{esc(v)}</b> {esc(k)}</span>' for k, v in pares
    ) + "</div>"


def _lista(items: list[str], clase: str = "") -> str:
    if not items:
        return ""
    return f'<ul class="sch-lista {clase}">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def _problema_html(p) -> str:
    donde = esc(p.hoja) if p.hoja else ""
    if p.fila is not None and donde:
        donde += f", fila {esc(p.fila)}"
    etiqueta = f'<span class="sch-donde">{donde}</span> ' if donde else ""
    return f"{etiqueta}{esc(p.mensaje)}"


def revision_html(rev: Revision) -> str:
    """Resultado de «Revisar archivo»."""
    avisos = _lista([_problema_html(p) for p in rev.advertencias])
    if rev.ok:
        r = rev.resumen
        chips = _chips(
            [
                ("profesores activos", r["profesores"]),
                ("materias", r["materias"]),
                ("grupos", r["grupos"]),
                ("sesiones por programar", r["sesiones"]),
                ("horas semanales", r["horas"]),
            ]
        )
        extra = chips + (
            f'<p class="sch-sub">Para tener en cuenta (no impide generar):</p>{avisos}' if avisos else ""
        )
        return banner("ok", "Tu archivo está en orden", f"Horario base: {r['calendario']}. Ya puedes generar el horario.", extra)
    errores = _lista([_problema_html(p) for p in rev.errores], "sch-errores")
    extra = errores + (f'<p class="sch-sub">Además:</p>{avisos}' if avisos else "")
    return banner(
        "warn",
        f"Hay {len(rev.errores)} dato(s) por corregir",
        "Corrígelos en tu Excel y vuelve a subirlo. No pasa nada: puedes repetirlo las veces que haga falta.",
        extra,
    )


_CLASE_ESTADO = {
    "LISTO": "ok",
    "SIN_SOLUCION": "warn",
    "INCONCLUSO": "info",
    "ENTRADA_INVALIDA": "warn",
    "NO_VERIFICADO": "err",
    "ERROR": "err",
}


def salida_html(s: Salida) -> str:
    """Estado del resultado tras «Generar horario»."""
    clase = _CLASE_ESTADO.get(s.estado, "info")
    extra = ""
    if s.exitoso:
        m = s.metricas
        extra += _chips(
            [
                ("sesiones programadas", m.get("sesiones", 0)),
                ("h de hueco en profesores", m.get("huecos_profesores", 0)),
                ("h de hueco en grupos", m.get("huecos_grupos", 0)),
                ("% de días docentes sin huecos", m.get("continuidad_pct", 100)),
                ("s de búsqueda", f"{s.segundos:.1f}"),
            ]
        )
    if s.avisos:
        extra += '<p class="sch-sub">Para tener en cuenta:</p>' + _lista([esc(a) for a in s.avisos])
    if s.sugerencias:
        extra += '<p class="sch-sub">Por dónde empezar a revisar:</p>' + _lista([esc(a) for a in s.sugerencias])
    if s.estado == "ENTRADA_INVALIDA" and s.revision is not None:
        extra += _lista([_problema_html(p) for p in s.revision.errores], "sch-errores")
    return banner(clase, s.titulo, s.mensaje, extra)


def acceso_html(vence_texto: str, abierto: bool = False) -> str:
    if abierto:
        return '<div class="sch-acceso">Modo de desarrollo: acceso abierto</div>'
    return f'<div class="sch-acceso">Acceso activo hasta el <b>{esc(vence_texto)}</b></div>'
