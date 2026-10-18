"""Estructuras de datos de Schedora.

Todo el motor trabaja con estas clases; ninguna depende de Gradio ni de OR-Tools.
Las horas se representan como enteros (7 = 07:00) porque la unidad de tiempo
del plan es de una hora.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]
NOMBRE_DIA = {
    "lunes": "Lunes",
    "martes": "Martes",
    "miercoles": "Miércoles",
    "jueves": "Jueves",
    "viernes": "Viernes",
    "sabado": "Sábado",
}

MISMA_MATERIA_MODOS = ("evitar", "obligatorio", "permitir")


class ErrorArchivo(Exception):
    """El archivo no se pudo abrir o no es un .xlsx aceptable.

    El mensaje está pensado para mostrarse tal cual a la persona usuaria.
    """


@dataclass(frozen=True)
class Problema:
    """Un hallazgo de validación (error que bloquea o advertencia informativa)."""

    nivel: str  # "error" | "advertencia"
    hoja: str
    fila: int | None
    mensaje: str

    @property
    def es_error(self) -> bool:
        return self.nivel == "error"

    def __str__(self) -> str:
        donde = self.hoja
        if self.fila is not None:
            donde += f", fila {self.fila}"
        return f"[{donde}] {self.mensaje}" if donde else self.mensaje


@dataclass
class Config:
    hora_inicio: int = 7
    hora_fin: int = 18
    dias: list[str] = field(default_factory=lambda: list(DIAS))
    limite_busqueda_segundos: int = 30
    # Pesos enteros: CP-SAT trabaja con coeficientes enteros.
    peso_continuidad: int = 1000  # base del peso docente: peso(p) = base // (1 + horas_objetivo)
    peso_grupos: int = 60  # costo por hora de hueco interno en un grupo
    peso_dias_docente: int = 20  # % del peso docente aplicado a cada día trabajado
    peso_misma_materia_dia: int = 40  # costo por repetir una materia el mismo día
    misma_materia_mismo_dia: str = "evitar"  # evitar | obligatorio | permitir
    semilla_busqueda: int | None = None  # con semilla: un solo hilo (determinista)
    num_workers: int = 4

    @property
    def horas_calendario(self) -> list[int]:
        return list(range(self.hora_inicio, self.hora_fin))


@dataclass
class Profesor:
    id: str
    nombre: str
    materias: set[str]
    horas_objetivo: float | None = None
    horas_maximas: int | None = None
    horas_minimas: int | None = None
    activo: bool = True


@dataclass
class Materia:
    id: str
    nombre: str
    duracion: int  # 1 o 2 horas


@dataclass
class Oferta:
    id: str
    grupo: str
    materia: str
    horas_semanales: int
    sesiones_semanales: int | None = None
    profesor_obligatorio: str | None = None
    dias_permitidos: list[str] | None = None


@dataclass
class FilaDisponibilidad:
    profesor_id: str
    dia: str
    hora_inicio: int
    hora_fin: int
    tipo: str  # DISPONIBLE | NO_DISPONIBLE
    fila: int | None = None


@dataclass
class Datos:
    profesores: list[Profesor] = field(default_factory=list)
    materias: list[Materia] = field(default_factory=list)
    ofertas: list[Oferta] = field(default_factory=list)
    disponibilidad: list[FilaDisponibilidad] = field(default_factory=list)
    config: Config = field(default_factory=Config)

    def profesor(self, pid: str) -> Profesor | None:
        return next((p for p in self.profesores if p.id == pid), None)

    def materia(self, mid: str) -> Materia | None:
        return next((m for m in self.materias if m.id == mid), None)

    @property
    def grupos(self) -> list[str]:
        vistos: list[str] = []
        for o in self.ofertas:
            if o.grupo not in vistos:
                vistos.append(o.grupo)
        return vistos


@dataclass(frozen=True)
class Sesion:
    """Unidad individual de programación (una clase de 1 o 2 horas)."""

    id: str  # "<oferta_id>#<n>"
    oferta_id: str
    grupo: str
    materia: str
    duracion: int
    indice: int


@dataclass(frozen=True)
class Asignacion:
    sesion_id: str
    oferta_id: str
    grupo: str
    materia: str
    profesor_id: str
    dia: str
    inicio: int
    duracion: int

    @property
    def fin(self) -> int:
        return self.inicio + self.duracion

    @property
    def bloques(self) -> range:
        return range(self.inicio, self.inicio + self.duracion)


def hora_texto(h: int) -> str:
    return f"{h:02d}:00"
