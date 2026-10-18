"""Construye la interfaz Gradio.

La API de Gradio cambia entre versiones mayores (por ejemplo, en algunas `theme`, `css` y
`js` se pasan a Blocks y en otras a launch()). `opciones_de_estilo` revisa las firmas
instaladas y reparte esos argumentos donde corresponde.
"""
from __future__ import annotations

import inspect
import os

import gradio as gr

from acceso.tokens import acceso_abierto
from scheduler import plantilla
from . import callbacks as cb
from . import render, tema

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EJEMPLOS = os.path.join(RAIZ, "examples")


def _soportados(funcion, **kwargs) -> dict:
    """Filtra kwargs a los que la función realmente acepta en la versión instalada."""
    try:
        permitidos = set(inspect.signature(funcion).parameters)
    except (TypeError, ValueError):
        return kwargs
    return {k: v for k, v in kwargs.items() if k in permitidos and v is not None}


def opciones_de_estilo() -> tuple[dict, dict]:
    """(kwargs para gr.Blocks, kwargs para launch) con theme/css/js donde la versión los acepte."""
    deseados = {"theme": tema.tema_gradio(), "css": tema.CSS, "js": tema.JS_FORZAR_CLARO}
    en_blocks = _soportados(gr.Blocks.__init__, **deseados)
    resto = {k: v for k, v in deseados.items() if k not in en_blocks and v is not None}
    en_launch = _soportados(gr.Blocks.launch, **resto)
    return en_blocks, en_launch


def _ruta_ejemplo(nombre: str, crear) -> str:
    """Archivo de ejemplo del repositorio; si falta, se regenera."""
    ruta = os.path.join(EJEMPLOS, nombre)
    if not os.path.exists(ruta):
        os.makedirs(EJEMPLOS, exist_ok=True)
        crear(ruta)
    return ruta


def construir_app():
    """Devuelve (demo, kwargs_de_launch)."""
    abierto = acceso_abierto()
    en_blocks, en_launch = opciones_de_estilo()
    en_blocks.update(_soportados(gr.Blocks.__init__, title="Schedora · Horarios docentes", delete_cache=(3600, 3600)))
    ruta_plantilla = _ruta_ejemplo("plantilla_horarios.xlsx", plantilla.crear_plantilla)
    ruta_ejemplo = _ruta_ejemplo("datos_validos.xlsx", plantilla.crear_ejemplo_valido)

    with gr.Blocks(**en_blocks) as demo:
        token = gr.State("abierto" if abierto else None)
        revision = gr.State(None)
        salida = gr.State(None)

        gr.HTML(tema.encabezado_html())

        # ------------------------------------------------ pantalla de acceso
        with gr.Column(visible=not abierto) as compuerta:
            gr.HTML(tema.bienvenida_html())
            codigo = gr.Textbox(
                label="Código de acceso",
                placeholder="SCH-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX",
                max_lines=1,
                autofocus=True,
            )
            entrar = gr.Button("Entrar", variant="primary", elem_classes="sch-primario")
            msg_acceso = gr.HTML()

        # ------------------------------------------------ aplicación
        with gr.Column(visible=abierto) as app:
            banner_acceso = gr.HTML(render.acceso_html("", True) if abierto else "")

            # Paso 1
            with gr.Group(elem_classes="sch-paso"):
                gr.HTML(
                    tema.paso_html(
                        1,
                        "Sube tu archivo de Excel",
                        "Usa nuestra plantilla para que todo encaje a la primera. Puedes descargar también un ejemplo para probar.",
                    )
                )
                archivo = gr.File(label="Archivo .xlsx", file_types=[".xlsx"], type="filepath")
                with gr.Row():
                    gr.DownloadButton("Descargar plantilla", value=ruta_plantilla, variant="secondary", elem_classes="sch-secundario")
                    gr.DownloadButton("Descargar ejemplo para probar", value=ruta_ejemplo, variant="secondary", elem_classes="sch-secundario")
                revisar = gr.Button("Revisar archivo", variant="primary", elem_classes="sch-primario")
                html_revision = gr.HTML()
                btn_diag_rev = gr.DownloadButton("Descargar reporte de revisión", visible=False, variant="secondary", elem_classes="sch-secundario")

            # Paso 2
            with gr.Group(elem_classes="sch-paso"):
                gr.HTML(
                    tema.paso_html(
                        2,
                        "Genera tu horario",
                        "Validamos cada regla antes de mostrarte el resultado. Más tiempo de búsqueda puede dar un horario más cómodo.",
                    )
                )
                segundos = gr.Slider(10, 60, value=30, step=5, label="Tiempo máximo de búsqueda (segundos)")
                generar = gr.Button("Generar horario", variant="primary", interactive=False, elem_classes="sch-primario")
                html_estado = gr.HTML()
                btn_diag = gr.DownloadButton("Descargar diagnóstico", visible=False, variant="secondary", elem_classes="sch-secundario")

            # Paso 3: resultados
            with gr.Group(elem_classes="sch-paso", visible=False) as resultados:
                gr.HTML(tema.paso_html(3, "Tu horario", "Cámbialo de vista para revisar cada grupo o cada profesor."))
                with gr.Row():
                    vista_tipo = gr.Radio(
                        choices=[("Por grupo", "grupo"), ("Por profesor", "profesor")],
                        value="grupo",
                        label="Ver",
                        visible=False,
                    )
                    vista_entidad = gr.Dropdown(choices=[], label="Seleccionar", visible=False, interactive=True)
                tabla = gr.Dataframe(label="Horario semanal", interactive=False, wrap=True, elem_classes="sch-tabla")
                tabla_carga = gr.Dataframe(label="Carga y continuidad por profesor", interactive=False, wrap=True, elem_classes="sch-tabla")
                with gr.Row():
                    btn_excel = gr.DownloadButton("Descargar horario en Excel", visible=False, variant="primary", elem_classes="sch-primario")
                    nuevo = gr.Button("Empezar con otro archivo", variant="secondary", elem_classes="sch-secundario")

            gr.HTML('<div class="sch-pie">Tus archivos se procesan en el momento y se eliminan; no se guardan en el servidor.</div>')

        # ------------------------------------------------ eventos
        acciones_entrar = dict(fn=cb.entrar, inputs=[codigo], outputs=[token, compuerta, app, msg_acceso, banner_acceso])
        entrar.click(**acciones_entrar)
        codigo.submit(**acciones_entrar)

        revisar.click(
            cb.revisar_archivo,
            inputs=[archivo, token],
            outputs=[revision, html_revision, generar, btn_diag_rev, resultados],
        )
        generar.click(
            cb.generar_horario,
            inputs=[revision, segundos, token],
            outputs=[salida, html_estado, resultados, vista_tipo, vista_entidad, tabla, tabla_carga, btn_excel, btn_diag],
            concurrency_limit=2,
        )
        vista_tipo.change(cb.cambiar_tipo, inputs=[salida, vista_tipo], outputs=[vista_entidad, tabla])
        vista_entidad.change(cb.cambiar_entidad, inputs=[salida, vista_tipo, vista_entidad], outputs=[tabla])
        nuevo.click(
            cb.reiniciar,
            outputs=[archivo, revision, salida, html_revision, html_estado, generar, resultados, btn_diag_rev],
        ).then(lambda: gr.update(visible=False), outputs=[btn_diag])

    demo.queue(**_soportados(demo.queue, max_size=20, default_concurrency_limit=2))
    lanzamiento = dict(en_launch)
    lanzamiento.update(_soportados(gr.Blocks.launch, allowed_paths=[EJEMPLOS], max_file_size="5mb", show_error=False, favicon_path=os.path.join(tema.ASSETS, "favicon.png")))
    return demo, lanzamiento
