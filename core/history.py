"""Historial reciente de cada conversación (lo que el cerebro ve como contexto)."""

from collections import deque

from core.memory import MemoryStore


class ConversationStore:
    """Mensajes recientes separados por chat.

    Con `store` (la base de datos) sobrevive a los reinicios; sin él, vive en la RAM.
    """

    def __init__(self, max_messages: int = 20, store: MemoryStore | None = None):
        self.max_messages = max_messages
        self.store = store
        self._chats: dict[str, deque] = {}
        self._private: set[str] = set()

    def get(self, chat_id: int | str) -> list[dict]:
        if self.store is not None:
            return self.store.recent_messages(str(chat_id), self.max_messages)
        return list(self._chats.get(str(chat_id), ()))

    def add_exchange(self, chat_id: int | str, user_text: str, assistant_text: str):
        if self.store is not None:
            self.store.add_messages(
                str(chat_id), [("user", user_text), ("assistant", assistant_text)]
            )
            self.store.prune_messages(str(chat_id), self.max_messages)
            return
        history = self._chats.setdefault(str(chat_id), deque(maxlen=self.max_messages))
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": assistant_text})

    def clear(self, chat_id: int | str):
        if self.store is not None:
            self.store.clear_messages(str(chat_id))
        self._chats.pop(str(chat_id), None)
        self._private.discard(str(chat_id))

    # Privacidad persistente: si una conversación tuvo algo privado, su historial también lo
    # es, y no puede viajar a la nube en el siguiente mensaje "normal". Dura hasta el reset.

    def mark_private(self, chat_id: int | str):
        if self.store is not None:
            self.store.mark_private(str(chat_id))
        self._private.add(str(chat_id))

    def is_private(self, chat_id: int | str) -> bool:
        if str(chat_id) in self._private:
            return True
        return self.store is not None and self.store.is_private(str(chat_id))
