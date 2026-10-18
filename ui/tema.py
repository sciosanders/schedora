"""Tema visual de Schedora: calma, claridad y control.

Paleta (de la imagen de marca):
    #0D7377 control y confianza      #14919B enfoque sereno      #A8D5BA relajación y equilibrio
    #F7F3E9 espacio limpio           #E9C46A positividad suave   #264653 estructura y claridad
Contraste sobre crema: #0D7377 ≈ 5:1 (texto y botones), #264653 alto; #14919B solo para
elementos grandes; #E9C46A nunca como texto, solo acento.
"""
from __future__ import annotations

import base64
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(RAIZ, "assets")

CSS = """
:root {
  --sch-teal: #0D7377; --sch-teal-2: #14919B; --sch-mint: #A8D5BA; --sch-crema: #F7F3E9;
  --sch-amarillo: #E9C46A; --sch-oscuro: #264653; --sch-papel: #FFFDF8; --sch-borde: #E4DECF;
}
/* Siempre claro: la paleta está pensada para fondo crema */
body, .gradio-container, .dark body, .dark .gradio-container {
  background: var(--sch-crema) !important; color: var(--sch-oscuro) !important;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
}
.gradio-container { max-width: 980px !important; margin: 0 auto !important; padding: 8px 20px 56px !important; }
footer { display: none !important; }

/* Encabezado */
.sch-encabezado { display: flex; align-items: center; gap: 14px; padding: 18px 2px 6px; }
.sch-encabezado img { width: 52px; height: 52px; }
.sch-marca { font-size: 1.55rem; font-weight: 700; letter-spacing: .01em; color: var(--sch-oscuro); line-height: 1.1; }
.sch-lema { color: var(--sch-teal); font-size: .98rem; margin-top: 2px; }
.sch-acceso { text-align: right; color: var(--sch-oscuro); font-size: .9rem; padding: 4px 2px; opacity: .85; }

/* Pantalla de acceso */
.sch-bienvenida { text-align: center; padding: 28px 0 6px; }
.sch-bienvenida img { width: 190px; max-width: 60%; }
.sch-bienvenida h2 { margin: 14px 0 6px; font-size: 1.35rem; color: var(--sch-oscuro); }
.sch-bienvenida p { margin: 0 auto; max-width: 440px; color: var(--sch-oscuro); opacity: .85; line-height: 1.5; }

/* Tarjetas por paso */
.sch-paso { background: var(--sch-papel) !important; border: 1px solid var(--sch-borde) !important; border-radius: 18px !important;
  padding: 20px 22px !important; margin-top: 16px !important; box-shadow: 0 1px 2px rgba(38,70,83,.05); }
.sch-paso-titulo { display: flex; align-items: center; gap: 12px; margin: 0 0 4px; }
.sch-num { display: inline-flex; width: 30px; height: 30px; border-radius: 50%; background: var(--sch-teal); color: #fff;
  align-items: center; justify-content: center; font-weight: 700; font-size: .95rem; flex: none; }
.sch-paso-titulo h3 { margin: 0; font-size: 1.15rem; color: var(--sch-oscuro); }
.sch-ayuda { margin: 2px 0 10px 42px; color: var(--sch-oscuro); opacity: .8; font-size: .94rem; line-height: 1.45; }

/* Mensajes */
.sch-banner { display: flex; gap: 14px; border-radius: 14px; padding: 14px 16px; margin: 10px 0 2px; border: 1px solid; }
.sch-b-icono { flex: none; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-weight: 700; color: #fff; margin-top: 1px; }
.sch-b-cuerpo { min-width: 0; flex: 1; }
.sch-b-titulo { margin: 0 0 2px; font-weight: 700; font-size: 1.04rem; color: var(--sch-oscuro); }
.sch-b-texto { margin: 2px 0 6px; color: var(--sch-oscuro); line-height: 1.5; }
.sch-ok { background: #E7F3EB; border-color: var(--sch-mint); } .sch-ok .sch-b-icono { background: var(--sch-teal); }
.sch-warn { background: #FBF2D9; border-color: var(--sch-amarillo); } .sch-warn .sch-b-icono { background: #8A6A12; }
.sch-err { background: #FBEBE6; border-color: #D9A08F; } .sch-err .sch-b-icono { background: #A4452F; }
.sch-info { background: #E3F1F2; border-color: var(--sch-teal-2); } .sch-info .sch-b-icono { background: var(--sch-teal); }
.sch-sub { margin: 10px 0 2px; font-weight: 600; color: var(--sch-oscuro); }
.sch-lista { margin: 4px 0 0 18px; padding: 0; color: var(--sch-oscuro); line-height: 1.5; }
.sch-lista li { margin: 3px 0; }
.sch-donde { font-weight: 600; color: var(--sch-teal); }
.sch-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 2px; }
.sch-chip { background: var(--sch-papel); border: 1px solid var(--sch-borde); border-radius: 999px; padding: 4px 12px; font-size: .9rem; color: var(--sch-oscuro); }
.sch-chip b { color: var(--sch-teal); }

/* Botones */
button.primary, .sch-primario button, .sch-primario {
  background: var(--sch-teal) !important; border-color: var(--sch-teal) !important; color: #fff !important; font-weight: 600 !important;
  border-radius: 12px !important;
}
button.primary:hover, .sch-primario:hover { background: #0B5F63 !important; }
button.secondary, .sch-secundario { border-radius: 12px !important; border: 1px solid var(--sch-teal) !important; color: var(--sch-teal) !important;
  background: transparent !important; font-weight: 600 !important; }
button:focus-visible, input:focus-visible, textarea:focus-visible, select:focus-visible { outline: 3px solid var(--sch-teal-2) !important; outline-offset: 2px; }
button[disabled] { opacity: .55 !important; }

/* Tablas del horario */
.sch-tabla table { font-size: .9rem; }
.sch-tabla th { background: var(--sch-teal) !important; color: #fff !important; }
.sch-pie { text-align: center; color: var(--sch-oscuro); opacity: .7; font-size: .85rem; margin-top: 28px; }
@media (max-width: 640px) {
  .gradio-container { padding: 6px 12px 40px !important; }
  .sch-paso { padding: 16px 14px !important; } .sch-ayuda { margin-left: 0; }
  .sch-marca { font-size: 1.3rem; }
}
"""


_MIME = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
_RAIZ = os.path.dirname(ASSETS)


def _buscar_imagen(base: str, alias: tuple[str, ...]) -> str | None:
    """Busca el logo: primero en la carpeta principal del proyecto (si lo agregaste ahí), luego en assets/."""
    for carpeta in (_RAIZ, ASSETS):
        for nombre in (base, *alias):
            for ext in (".svg", ".png", ".webp", ".jpg", ".jpeg"):
                ruta = os.path.join(carpeta, nombre + ext)
                if os.path.isfile(ruta):
                    return ruta
    return None


def _data_uri(nombre_svg: str) -> str:
    base = os.path.splitext(nombre_svg)[0]
    alias = ("logo",) if base.endswith("logo") else ("icono", "icon", "favicon")
    ruta = _buscar_imagen(base, alias)
    if not ruta:
        return ""
    try:
        with open(ruta, "rb") as f:
            return f"data:{_MIME[os.path.splitext(ruta)[1]]};base64," + base64.b64encode(f.read()).decode("ascii")
    except OSError:
        return ""


def encabezado_html() -> str:
    return (
        '<div class="sch-encabezado">'
        f'<img src="{_data_uri("schedora-icono.svg")}" alt="">'
        '<div><div class="sch-marca">Schedora</div>'
        '<div class="sch-lema">Tu horario, en orden y sin prisa.</div></div></div>'
    )


def bienvenida_html() -> str:
    return (
        '<div class="sch-bienvenida">'
        f'<img src="{_data_uri("schedora-logo.svg")}" alt="Schedora">'
        "<h2>Bienvenida/o</h2>"
        "<p>Escribe el código de acceso que recibiste para empezar. Tus archivos se procesan solo mientras trabajas y no se guardan.</p>"
        "</div>"
    )


def paso_html(numero: int, titulo: str, ayuda: str = "") -> str:
    ayuda_html = f'<p class="sch-ayuda">{ayuda}</p>' if ayuda else ""
    return f'<div class="sch-paso-titulo"><span class="sch-num">{numero}</span><h3>{titulo}</h3></div>{ayuda_html}'


def tema_gradio():
    """Tema de Gradio; si la versión instalada no acepta algún ajuste, se usa el predeterminado.

    La mayor parte del estilo vive en CSS para depender lo menos posible de la API del tema.
    """
    try:
        import gradio as gr

        teal = gr.themes.Color(
            c50="#E8F4F4", c100="#CFE7E8", c200="#A5D0D2", c300="#76B6B9", c400="#3F9EA4",
            c500="#14919B", c600="#0D7377", c700="#0B5F63", c800="#094B4F", c900="#073A3D", c950="#052B2E",
            name="schedora",
        )
        base = gr.themes.Base(
            primary_hue=teal,
            secondary_hue=teal,
            neutral_hue=gr.themes.colors.stone,
            radius_size=gr.themes.sizes.radius_lg,
            font=["system-ui", "Segoe UI", "Roboto", "Arial", "sans-serif"],
        )
        return base.set(
            body_background_fill="#F7F3E9",
            body_background_fill_dark="#F7F3E9",
            body_text_color="#264653",
            body_text_color_dark="#264653",
            block_background_fill="#FFFDF8",
            block_background_fill_dark="#FFFDF8",
            block_border_color="#E4DECF",
            block_border_color_dark="#E4DECF",
            button_primary_background_fill="#0D7377",
            button_primary_background_fill_hover="#0B5F63",
            button_primary_text_color="#FFFFFF",
        )
    except Exception:
        return None


JS_FORZAR_CLARO = "() => { document.body.classList.remove('dark'); }"
