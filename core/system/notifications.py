"""Notificaciones de Windows para la isla (estilo Samsung Brief).

Se leen con `UserNotificationListener` (WinRT; requiere winrt-Windows.UI.Notifications.Management
y winrt-Windows.ApplicationModel). Son **privadas por diseño**: solo viajan por el WebSocket local
de la mascota; nunca entran en la memoria, en un prompt ni en el MCP. Antes de publicarlas:
- solo pasan las apps permitidas (`system.notifications.apps`, "*" = todas) y no las bloqueadas;
- los códigos de verificación se ocultan;
- si el texto parece sensible (contraseñas, tarjetas, llaves: ai/privacy.py), se oculta entero.

Acciones posibles: descartar y abrir la app que la envió. Windows no permite pulsar los botones
de las notificaciones de otras apps (p. ej. "Responder" de WhatsApp).
"""

import re
import subprocess

from ai import privacy
from core.logger import setup_logger

logger = setup_logger("System")

NOTIFICATION_ACTIONS = ("dismiss", "open")
CODE_CONTEXT = re.compile(
    r"c[óo]digo|code|verificaci[óo]n|verification|otp|pin\b|2fa|token|one[- ]time|contraseña",
    re.IGNORECASE,
)
CODE = re.compile(r"\b(?:[A-Z]-)?\d{4,8}\b|\b\d{3}[ -]\d{3}\b")
HIDDEN = "🔒 Contenido oculto por privacidad"
SAFE_AUMID = re.compile(r"^[\w.!\- ]{1,200}$")


def protect(text: str | None, *, hide_codes: bool) -> str | None:
    """Oculta códigos de verificación y textos sensibles."""
    if not text:
        return text
    if privacy.detect(text):
        return HIDDEN
    if hide_codes and CODE_CONTEXT.search(text):
        return CODE.sub("••••••", text)
    return text


def allowed(app: str, aumid: str, apps: list[str], blocked: list[str]) -> bool:
    names = {app.lower(), aumid.lower()}
    if any(b.lower() in names for b in blocked):
        return False
    return "*" in apps or any(a.lower() in names for a in apps)


class NullNotificationSource:
    available = False

    async def snapshot(self) -> list[dict]:
        return []

    async def dismiss(self, notification_id: int) -> bool:
        return False

    async def open(self, aumid: str) -> bool:
        return False


class WindowsNotificationSource:
    available = True

    def __init__(self):
        from winrt.windows.ui.notifications import NotificationKinds
        from winrt.windows.ui.notifications.management import UserNotificationListener

        self._kinds = NotificationKinds.TOAST
        self._listener = UserNotificationListener.current
        self._checked = False

    async def snapshot(self) -> list[dict]:
        if not self._checked:
            access = await self._listener.request_access_async()
            self._checked = True
            if int(access) != 1:  # 1 = Allowed
                logger.warning(
                    "Windows no da acceso a las notificaciones (Configuración → Privacidad)"
                )
        items = []
        for n in await self._listener.get_notifications_async(self._kinds):
            binding = n.notification.visual.get_binding("ToastGeneric")
            texts = [t.text for t in binding.get_text_elements()] if binding else []
            info = n.app_info
            items.append({
                "id": int(n.id),
                "app": info.display_info.display_name or "Windows",
                "aumid": info.app_user_model_id or "",
                "title": texts[0] if texts else None,
                "body": "\n".join(texts[1:]) or None,
                "time": n.creation_time.timestamp(),
            })  # fmt: skip
        return items

    async def dismiss(self, notification_id: int) -> bool:
        self._listener.remove_notification(int(notification_id))
        return True

    async def open(self, aumid: str) -> bool:
        if not SAFE_AUMID.match(aumid or ""):
            return False
        # Lanza la app registrada con ese identificador (sin shell)
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{aumid}"])
        return True


def build_notification_source():
    try:
        return WindowsNotificationSource()
    except Exception as e:  # Fuera de Windows o sin las dependencias
        logger.info(f"Notificaciones del sistema no disponibles ({type(e).__name__})")
        return NullNotificationSource()


def present(item: dict, *, hide_codes: bool) -> dict:
    """Lo que se publica: sin el identificador interno de la app y con la privacidad aplicada."""
    return {
        "id": item["id"],
        "app": item["app"],
        "title": protect(item.get("title"), hide_codes=hide_codes),
        "body": protect(item.get("body"), hide_codes=hide_codes),
        "time": item["time"],
    }
