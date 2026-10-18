"""Generación de la plantilla de Excel y de los libros de ejemplo (datos ficticios)."""
from __future__ import annotations

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

TEAL = "0D7377"
CREMA = "F7F3E9"
OSCURO = "264653"

COLUMNAS = {
    "PROFESORES": ["profesor_id", "nombre", "materias", "horas_objetivo_semana", "horas_maximas_semana", "horas_minimas_semana", "activo"],
    "MATERIAS": ["materia_id", "nombre_materia", "duracion_sesion"],
    "OFERTA_ACADEMICA": ["oferta_id", "grupo_id", "materia_id", "horas_semanales", "sesiones_semanales", "profesor_obligatorio", "dias_permitidos"],
    "DISPONIBILIDAD": ["profesor_id", "dia", "hora_inicio", "hora_fin", "tipo"],
    "CONFIGURACION": ["clave", "valor"],
}

INSTRUCCIONES = [
    ("Cómo llenar este libro", None),
    ("1.", "Llena las hojas PROFESORES, MATERIAS y OFERTA_ACADEMICA. DISPONIBILIDAD y CONFIGURACION son opcionales."),
    ("2.", "Una fila por profesor, por materia y por necesidad académica (un grupo recibe una materia N horas a la semana)."),
    ("3.", "En PROFESORES, «materias» lleva los materia_id que puede impartir, separados por coma (MAT, ESP)."),
    ("4.", "duracion_sesion es 1 o 2 horas. Las horas_semanales de la oferta deben ser múltiplo de esa duración."),
    ("5.", "DISPONIBILIDAD: sin filas, el profesor está libre todo el horario. Con filas DISPONIBLE, solo esos intervalos. Con filas NO_DISPONIBLE, todo menos esos intervalos. Si se cruzan, gana NO_DISPONIBLE."),
    ("6.", "Las horas van en punto (07:00, 08:00…). El horario general es de 07:00 a 18:00, de lunes a sábado; se puede cambiar en CONFIGURACION."),
    ("7.", "horas_objetivo_semana es la carga que el profesor debería tener; se usa para dar prioridad a que los profesores con menos horas tengan clases seguidas. horas_maximas y horas_minimas SÍ son obligatorias."),
    ("8.", "profesor_obligatorio (opcional) fija quién imparte una oferta. dias_permitidos (opcional) limita los días, por ejemplo: lunes, miércoles."),
    ("9.", "Borra las filas de ejemplo antes de subir tus datos reales. No uses fórmulas: solo se leen valores."),
]

# ---------------------------------------------------------------- ejemplo válido
PROFESORES = [
    ("P01", "Ana Torres", "MAT", 16, 18, None, "si"),
    ("P02", "Luis Mendoza", "ESP", 16, 18, None, "si"),
    ("P03", "Carla Ruiz", "ING, HIS", 20, 22, None, "si"),
    ("P04", "Diego Salas", "CIE", 16, 18, None, "si"),
    ("P05", "Marta León", "EDF", 8, 10, None, "si"),
    ("P06", "Pablo Reyes", "MAT, CIE", 4, 8, None, "no"),
]
MATERIAS = [
    ("MAT", "Matemáticas", 2),
    ("ESP", "Español", 2),
    ("ING", "Inglés", 1),
    ("CIE", "Ciencias", 2),
    ("HIS", "Historia", 1),
    ("EDF", "Educación Física", 2),
]
_HORAS = {"MAT": 4, "ESP": 4, "ING": 3, "CIE": 4, "HIS": 2, "EDF": 2}
GRUPOS = ["1A", "1B", "2A", "2B"]
DISPONIBILIDAD = [
    ("P05", "lunes", "08:00", "12:00", "DISPONIBLE"),
    ("P05", "miercoles", "08:00", "12:00", "DISPONIBLE"),
    ("P05", "viernes", "08:00", "12:00", "DISPONIBLE"),
    ("P03", "sabado", "07:00", "18:00", "NO_DISPONIBLE"),
    ("P03", "martes", "07:00", "10:00", "NO_DISPONIBLE"),
    ("P01", "viernes", "14:00", "18:00", "NO_DISPONIBLE"),
]


def _ofertas_validas():
    filas = []
    n = 1
    for g in GRUPOS:
        for mid, h in _HORAS.items():
            filas.append((f"O{n:02d}", g, mid, h, None, None, None))
            n += 1
    return filas


# --------------------------------------------------- ejemplo infactible (previo)
def _variante_infactible_previa():
    """Educación Física pide más horas de las que su única profesora puede dar."""
    ofertas = _ofertas_validas()
    disp = [f for f in DISPONIBILIDAD if f[0] != "P05"]
    disp += [("P05", "lunes", "08:00", "10:00", "DISPONIBLE")]  # solo 2 h disponibles para 8 h de EDF
    return PROFESORES, MATERIAS, ofertas, disp


# ------------------------------------------------- ejemplo infactible (solver)
def _variante_infactible_solver():
    """Un profesor es el único para dos materias y solo tiene dos horas libres el lunes.

    Cada materia, por separado, cabe; juntas se empalman. Las verificaciones previas no lo
    detectan: lo demuestra el optimizador (INFEASIBLE) y el diagnóstico sugiere relajar la
    disponibilidad.
    """
    profesores = [("X01", "Elena Vidal", "MAT, ESP", 4, None, None, "si")]
    materias = [("MAT", "Matemáticas", 2), ("ESP", "Español", 2)]
    ofertas = [("O01", "1A", "MAT", 2, None, None, None), ("O02", "1A", "ESP", 2, None, None, None)]
    disp = [("X01", "lunes", "08:00", "10:00", "DISPONIBLE")]
    return profesores, materias, ofertas, disp


def _estilo_encabezado(ws, ncols: int):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=TEAL)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(c)].width = max(16, len(str(cell.value)) + 4)
    ws.freeze_panes = "A2"


def _escribir(ws, nombre: str, filas):
    ws.append(COLUMNAS[nombre])
    for f in filas:
        ws.append(list(f))
    _estilo_encabezado(ws, len(COLUMNAS[nombre]))


def _validaciones(wb: Workbook):
    dias = '"lunes,martes,miercoles,jueves,viernes,sabado"'
    dv_dia = DataValidation(type="list", formula1=dias, allow_blank=True)
    dv_tipo = DataValidation(type="list", formula1='"DISPONIBLE,NO_DISPONIBLE"', allow_blank=False)
    dv_dur = DataValidation(type="list", formula1='"1,2"', allow_blank=False)
    dv_act = DataValidation(type="list", formula1='"si,no"', allow_blank=True)
    wb["DISPONIBILIDAD"].add_data_validation(dv_dia)
    wb["DISPONIBILIDAD"].add_data_validation(dv_tipo)
    wb["MATERIAS"].add_data_validation(dv_dur)
    wb["PROFESORES"].add_data_validation(dv_act)
    dv_dia.add("B2:B500")
    dv_tipo.add("E2:E500")
    dv_dur.add("C2:C500")
    dv_act.add("G2:G500")


def _libro(ruta: str, profesores, materias, ofertas, disp, config=None, instrucciones=False):
    wb = Workbook()
    ws = wb.active
    ws.title = "PROFESORES"
    _escribir(ws, "PROFESORES", profesores)
    _escribir(wb.create_sheet("MATERIAS"), "MATERIAS", materias)
    _escribir(wb.create_sheet("OFERTA_ACADEMICA"), "OFERTA_ACADEMICA", ofertas)
    _escribir(wb.create_sheet("DISPONIBILIDAD"), "DISPONIBILIDAD", disp)
    _escribir(wb.create_sheet("CONFIGURACION"), "CONFIGURACION", config or [])
    _validaciones(wb)
    if instrucciones:
        wi = wb.create_sheet("INSTRUCCIONES", 0)
        wi.sheet_view.showGridLines = False
        wi.column_dimensions["A"].width = 6
        wi.column_dimensions["B"].width = 120
        wi["A1"] = INSTRUCCIONES[0][0]
        wi["A1"].font = Font(name="Calibri", bold=True, size=14, color=OSCURO)
        for i, (k, v) in enumerate(INSTRUCCIONES[1:], start=3):
            wi.cell(row=i, column=1, value=k).font = Font(name="Calibri", bold=True, color=TEAL)
            c = wi.cell(row=i, column=2, value=v)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.font = Font(name="Calibri", color=OSCURO)
        wb.active = 0
    wb.properties.creator = "Schedora"
    wb.save(ruta)
    return ruta


def crear_plantilla(ruta: str) -> str:
    """Plantilla vacía con encabezados, listas desplegables e instrucciones."""
    return _libro(ruta, [], [], [], [], config=[], instrucciones=True)


def crear_ejemplo_valido(ruta: str) -> str:
    return _libro(ruta, PROFESORES, MATERIAS, _ofertas_validas(), DISPONIBILIDAD, instrucciones=True)


def crear_ejemplo_infactible(ruta: str) -> str:
    """Infactible detectable antes de ejecutar el optimizador."""
    p, m, o, d = _variante_infactible_previa()
    return _libro(ruta, p, m, o, d)


def crear_ejemplo_infactible_solver(ruta: str) -> str:
    """Infactible que solo el optimizador demuestra (necesita OR-Tools)."""
    p, m, o, d = _variante_infactible_solver()
    return _libro(ruta, p, m, o, d)
