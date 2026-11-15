"""Los avisos de Hanna en el móvil: Telegram escucha a MEKA Core y reenvía lo que toca.

Solo lo que el núcleo marca con `remote` (no estás frente al equipo, `proactive.remote`):
- `reminder.due` → el aviso con botones «✅ Hecho», «⏰ 10 min» y «⏰ 1 h».
- `nudge` → el resumen apto para salir del equipo (`shareable`: sin tareas privadas ni
  notificaciones de Windows).
Solo al dueño (el primer ID de ALLOWED_USER_IDS). Sin dueño, no se reenvía nada.

También: `/tareas` (lista sin las privadas) y los botones de cada aviso.
"""

import asyncio
import contextlib
import json

import websockets
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from channels.client import CoreClient, CoreRequestError, CoreUnavailableError
from core.logger import setup_logger

logger = setup_logger("Telegram")

SNOOZE = {"s10": 10, "s60": 60}


def reminder_buttons(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Hecho", callback_data=f"task:done:{task_id}"),
        InlineKeyboardButton("⏰ 10 min", callback_data=f"task:s10:{task_id}"),
        InlineKeyboardButton("⏰ 1 h", callback_data=f"task:s60:{task_id}"),
    ]])  # fmt: skip


def to_phone(message: dict) -> tuple[str, InlineKeyboardMarkup | None] | None:
    """(texto, botones) si el evento debe llegar al móvil; None si no."""
    data = message.get("data") or {}
    if not data.get("remote"):
        return None
    if message.get("type") == "reminder.due" and not data.get("private"):
        return data["text"], reminder_buttons(int(data["id"]))
    if message.get("type") == "nudge" and data.get("shareable"):
        return data["shareable"], None
    return None


async def forward_alerts(bot, core: CoreClient, owner: int, *, retry: float = 5.0):
    """Escucha el WebSocket del núcleo y reenvía los avisos. Se reconecta si el núcleo cae."""
    delay = retry
    while True:
        try:
            async with websockets.connect(core.events_url()) as ws:
                await ws.send(json.dumps({"type": "client.hello", "data": {"client": "telegram"}}))
                logger.info("Avisos de Hanna conectados: llegarán aquí cuando no estés al equipo")
                delay = retry
                async for raw in ws:
                    with contextlib.suppress(ValueError, KeyError, TypeError):
                        alert = to_phone(json.loads(raw))
                        if alert is not None:
                            text, buttons = alert
                            await bot.send_message(owner, text, reply_markup=buttons)
                            logger.info("Aviso enviado a Telegram")
        except asyncio.CancelledError:
            raise
        except Exception as e:  # Núcleo reiniciándose, red caída...
            logger.warning(f"Avisos desconectados ({type(e).__name__}); reintento en {delay:.0f} s")
        await asyncio.sleep(delay)
        delay = min(delay * 2, 60)


# ---------------------------------------------------------------------- manejadores


def _core(context: ContextTypes.DEFAULT_TYPE) -> CoreClient:
    return context.application.bot_data["core"]


async def task_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Los botones de un aviso: hecha o posponer."""
    query = update.callback_query
    allowed = context.application.bot_data.get("allowed_ids") or set()
    if allowed and update.effective_user.id not in allowed:
        await query.answer("No autorizado")
        return
    try:
        _, action, task_id = query.data.split(":")
        user = str(update.effective_user.id)
        if action == "done":
            await _core(context).task_action(user, int(task_id), "done")
            note = "✅ ¡Hecha!"
        else:
            minutes = SNOOZE[action]
            await _core(context).task_action(user, int(task_id), "snooze", minutes=minutes)
            note = (
                f"⏰ Te lo recuerdo en {minutes} min"
                if minutes < 60
                else "⏰ Te lo recuerdo en 1 h"
            )
    except CoreRequestError:  # Antes que ValueError: hereda de ella
        await query.answer("Esa tarea ya no existe")
        return
    except (ValueError, KeyError):
        await query.answer("Botón no válido")
        return
    except CoreUnavailableError:
        await query.answer("MEKA Core no responde ahora mismo")
        return
    await query.answer(note)
    with contextlib.suppress(Exception):  # Mensajes muy antiguos no se pueden editar
        await query.edit_message_text(f"{query.message.text}\n\n{note}")


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tareas: lo pendiente (sin las tareas privadas: Telegram está fuera del equipo)."""
    tasks = await _core(context).tasks(str(update.effective_user.id), include_private=False)
    if not tasks:
        await update.effective_message.reply_text("No tienes nada pendiente. ¡Todo al día! ✅")
        return
    lines = ["Tus pendientes:"] + [f"• {t['title']}" for t in tasks[:20]]
    await update.effective_message.reply_text("\n".join(lines))
