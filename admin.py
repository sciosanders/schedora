"""Herramienta de administración de accesos (se ejecuta en TU computadora, no en Azure).

Necesita la misma variable SCHEDORA_SECRET que configuraste en Render.

    python admin.py crear --escuela "Primaria Benito Juárez" --dias 5
    python admin.py verificar SCH-XXXX-...
    python admin.py revocar-ayuda

El registro de códigos emitidos se guarda en accesos.csv (local, fuera de git).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime

from acceso.tokens import (
    crear_codigo,
    fin_de_dia_unix,
    obtener_revocados,
    obtener_secreto,
    verificar_codigo,
    zona_horaria,
)

REGISTRO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accesos.csv")


def _secreto_o_salir() -> bytes:
    s = obtener_secreto()
    if s is None:
        sys.exit(
            "Falta la variable de entorno SCHEDORA_SECRET (mínimo 16 caracteres).\n"
            "  Linux/Mac:  export SCHEDORA_SECRET='tu-secreto-largo'\n"
            "  Windows:    set SCHEDORA_SECRET=tu-secreto-largo\n"
            "Debe ser exactamente la misma que configures en Render."
        )
    return s


def cmd_crear(args) -> None:
    if args.dias < 0 or args.dias > 365:
        sys.exit("--dias debe estar entre 0 y 365.")
    secreto = _secreto_o_salir()
    vence = fin_de_dia_unix(args.dias)
    codigo, id_hex = crear_codigo(secreto, vence)
    fecha = datetime.fromtimestamp(vence, zona_horaria()).strftime("%d/%m/%Y %H:%M")
    nuevo = not os.path.exists(REGISTRO)
    with open(REGISTRO, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["id", "escuela", "creado", "vence", "nota"])
        w.writerow([id_hex, args.escuela, datetime.now(zona_horaria()).strftime("%Y-%m-%d %H:%M"), fecha, args.nota or ""])
    print()
    print(f"  Escuela:  {args.escuela}")
    print(f"  Vence:    {fecha} ({zona_horaria().key})")
    print(f"  ID:       {id_hex}   (guárdalo: sirve para desactivarlo antes)")
    print()
    print(f"  CÓDIGO:   {codigo}")
    print()


def cmd_verificar(args) -> None:
    secreto = _secreto_o_salir()
    r = verificar_codigo(args.codigo, secreto, obtener_revocados(), time.time())
    estado = "VÁLIDO" if r.valido else "NO VÁLIDO"
    print(f"{estado}: {r.mensaje}")
    if r.id:
        print(f"ID: {r.id}   Vence: {r.vence_texto()}")


def cmd_revocar_ayuda(_args) -> None:
    print(
        "Para desactivar un acceso antes de que venza:\n"
        "  1. En Azure Portal, abre tu App Service > Configuración > Variables de entorno.\n"
        "  2. Edita SCHEDORA_REVOCADOS y agrega el ID del acceso (8 caracteres),\n"
        "     separado por comas de los demás:  a1b2c3d4,e5f6a7b8\n"
        "  3. Aplica y guarda. Azure reinicia la app y el acceso deja de funcionar.\n"
        "Los IDs emitidos están en accesos.csv.\n"
        "Cuando un acceso ya venció, puedes quitar su ID de la lista."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Administración de accesos de Schedora")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crear", help="Crear un código de acceso temporal")
    c.add_argument("--escuela", required=True, help="Nombre de la escuela o persona (solo para tu registro)")
    c.add_argument("--dias", type=int, default=5, help="Días de acceso; vence al final del día de hoy + N (por defecto 5)")
    c.add_argument("--nota", default="", help="Nota opcional para tu registro (pago, folio…)")
    c.set_defaults(fn=cmd_crear)
    v = sub.add_parser("verificar", help="Comprobar si un código es válido")
    v.add_argument("codigo")
    v.set_defaults(fn=cmd_verificar)
    r = sub.add_parser("revocar-ayuda", help="Cómo desactivar un acceso antes de tiempo")
    r.set_defaults(fn=cmd_revocar_ayuda)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
