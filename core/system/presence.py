"""¿Estás frente al equipo? Segundos sin tocar teclado ni ratón (Windows: GetLastInputInfo).

Sin dependencias ni permisos: es la misma cuenta que usa Windows para el salvapantallas. No
dice qué haces, solo cuánto hace que no tocas nada. Fuera de Windows devuelve None.
"""

import ctypes
import sys


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def idle_seconds() -> float | None:
    if sys.platform != "win32":
        return None
    info = _LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return None
    # GetTickCount da la vuelta cada 49 días: se compara con aritmética de 32 bits
    now = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
    return ((now - info.dwTime) & 0xFFFFFFFF) / 1000
