"""Códigos de acceso temporales, sin base de datos.

Un código contiene (id aleatorio, vencimiento) y una firma HMAC-SHA256 calculada con
un secreto del servidor. El servidor solo verifica la firma y la fecha: no guarda nada.

Formato: SCH-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX  (15 bytes en base32 = 24 caracteres)
    4 bytes id  |  4 bytes vencimiento (unix, UTC)  |  7 bytes firma

Desactivar antes del vencimiento: agregar el ID del código (8 caracteres hex) a la
variable de entorno SCHEDORA_REVOCADOS, separado por comas.

Falla cerrado: si SCHEDORA_SECRET no está definido (o es corto), ningún código es válido,
salvo que se active explícitamente SCHEDORA_ACCESO_ABIERTO=1 (solo para desarrollo local).
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import struct
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PREFIJO = "SCH"
LARGO_ID = 4
LARGO_FIRMA = 7
MIN_SECRETO = 16


def zona_horaria() -> ZoneInfo:
    try:
        return ZoneInfo(os.environ.get("SCHEDORA_TZ", "America/Hermosillo"))
    except Exception:
        return ZoneInfo("UTC")


def acceso_abierto() -> bool:
    return os.environ.get("SCHEDORA_ACCESO_ABIERTO", "").strip() == "1"


def obtener_secreto() -> bytes | None:
    s = os.environ.get("SCHEDORA_SECRET", "")
    return s.encode("utf-8") if len(s) >= MIN_SECRETO else None


def obtener_revocados() -> set[str]:
    crudo = os.environ.get("SCHEDORA_REVOCADOS", "")
    return {x.strip().lower() for x in crudo.replace(";", ",").split(",") if x.strip()}


@dataclass(frozen=True)
class ResultadoAcceso:
    valido: bool
    mensaje: str
    id: str = ""
    vence: int = 0  # unix UTC

    def vence_texto(self) -> str:
        if not self.vence:
            return ""
        return datetime.fromtimestamp(self.vence, zona_horaria()).strftime("%d/%m/%Y")


def fin_de_dia_unix(dias: int, ahora: float | None = None) -> int:
    """Vence al terminar (23:59:59, hora local configurada) el día de hoy + `dias`."""
    tz = zona_horaria()
    hoy = datetime.fromtimestamp(ahora if ahora is not None else time.time(), tz)
    destino = (hoy + timedelta(days=dias)).replace(hour=23, minute=59, second=59, microsecond=0)
    return int(destino.timestamp())


def _firmar(secreto: bytes, carga: bytes) -> bytes:
    return hmac.new(secreto, carga, hashlib.sha256).digest()[:LARGO_FIRMA]


def crear_codigo(secreto: bytes, vence: int, id_bytes: bytes | None = None) -> tuple[str, str]:
    """Devuelve (codigo, id_hex). `vence` es un entero unix en UTC."""
    if len(secreto) < MIN_SECRETO:
        raise ValueError(f"El secreto debe tener al menos {MIN_SECRETO} caracteres.")
    id_bytes = id_bytes or os.urandom(LARGO_ID)
    carga = id_bytes + struct.pack(">I", int(vence))
    crudo = carga + _firmar(secreto, carga)
    b32 = base64.b32encode(crudo).decode("ascii").rstrip("=")
    grupos = [b32[i : i + 4] for i in range(0, len(b32), 4)]
    return f"{PREFIJO}-" + "-".join(grupos), id_bytes.hex()


def _normalizar(codigo: str) -> str:
    c = "".join(ch for ch in (codigo or "").upper() if ch.isalnum())
    if c.startswith(PREFIJO):
        c = c[len(PREFIJO) :]
    return c


def verificar_codigo(
    codigo: str,
    secreto: bytes | None = None,
    revocados: set[str] | None = None,
    ahora: float | None = None,
) -> ResultadoAcceso:
    """Valida firma, revocación y vencimiento. Mensajes pensados para la persona usuaria."""
    secreto = secreto if secreto is not None else obtener_secreto()
    if secreto is None:
        return ResultadoAcceso(False, "El servicio todavía no está configurado para recibir accesos.")
    c = _normalizar(codigo)
    generico = "No reconocemos ese código. Revisa que esté completo y sin errores de captura."
    if not c:
        return ResultadoAcceso(False, "Escribe tu código de acceso.")
    try:
        crudo = base64.b32decode(c + "=" * (-len(c) % 8))
    except (binascii.Error, ValueError):
        return ResultadoAcceso(False, generico)
    if len(crudo) != LARGO_ID + 4 + LARGO_FIRMA:
        return ResultadoAcceso(False, generico)
    carga, firma = crudo[: LARGO_ID + 4], crudo[LARGO_ID + 4 :]
    if not hmac.compare_digest(firma, _firmar(secreto, carga)):
        return ResultadoAcceso(False, generico)
    id_hex = carga[:LARGO_ID].hex()
    (vence,) = struct.unpack(">I", carga[LARGO_ID:])
    revocados = revocados if revocados is not None else obtener_revocados()
    if id_hex in revocados:
        return ResultadoAcceso(False, "Este acceso fue desactivado. Si crees que es un error, escríbenos.", id_hex, vence)
    ahora = ahora if ahora is not None else time.time()
    if ahora > vence:
        fecha = datetime.fromtimestamp(vence, zona_horaria()).strftime("%d/%m/%Y")
        return ResultadoAcceso(False, f"Este acceso terminó el {fecha}. Escríbenos si quieres renovarlo.", id_hex, vence)
    return ResultadoAcceso(True, "Acceso activo", id_hex, vence)
