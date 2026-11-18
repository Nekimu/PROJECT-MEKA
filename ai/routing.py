"""Enrutamiento del cerebro (filosofía híbrida §5.3): qué proveedor atiende cada tarea y
qué pasa con lo privado.

    ai:
      provider: "claude"           # Por defecto, para todo
      routing: {vision: "gemini", document: "ollama"}
      fallback_provider: "ollama"  # Si el elegido falla o se niega
      privacy: {provider: "ollama"}
      local_only: false            # true = nada sale del equipo

Regla de oro: una petición privada **nunca** llega a un proveedor en la nube, ni siquiera
como respaldo. Si no hay proveedor local disponible, no se envía.
"""

from ai.providers import Provider, ProviderError
from core.logger import setup_logger

logger = setup_logger("AI_Router")

TASKS = ("chat", "vision", "document")


class PrivacyError(ProviderError):
    """Petición privada sin ningún proveedor local que la atienda."""


class CapabilityError(ProviderError):
    """Ningún cerebro de la ruta entiende lo que se le quiere enviar (audio, PDF...)."""


class Router:
    def __init__(self, ai_config: dict, providers: dict[str, Provider]):
        primary = ai_config.get("provider", "ollama")
        routes = ai_config.get("routing") or {}
        self.routes = {
            "chat": routes.get("chat") or primary,
            # vision_provider se mantiene por compatibilidad con config.yml anteriores
            "vision": routes.get("vision") or ai_config.get("vision_provider") or primary,
            "document": routes.get("document") or primary,
        }
        self.fallback = ai_config.get("fallback_provider") or None
        self.private = (ai_config.get("privacy") or {}).get("provider") or "ollama"
        self.local_only = bool(ai_config.get("local_only", False))
        self.providers = providers

    @staticmethod
    def needed(ai_config: dict) -> list[str]:
        """Proveedores que hay que crear según la configuración."""
        router = Router(ai_config, {})
        names = [*router.routes.values(), router.fallback, router.private]
        return [n for n in dict.fromkeys(names) if n]

    def enforce_local(self):
        """`ai.local_only`: los proveedores en la nube se ignoran por completo."""
        cloud = sorted(n for n, p in self.providers.items() if not p.local)
        if not cloud:
            return
        logger.warning(f"ai.local_only activo: se ignoran {', '.join(cloud)}")
        for task, name in self.routes.items():
            if name in cloud:
                self.routes[task] = self.private
        if self.fallback in cloud:
            self.fallback = None

    def order(
        self, task: str = "chat", *, private: bool = False, need: str | None = None
    ) -> list[str]:
        """Proveedores a probar, en orden, para una tarea. Con `need` ("audio", "pdf"...),
        solo los que lo entienden de forma nativa."""
        names = self._order(task, private=private)
        if need is None:
            return names
        capable = [n for n in names if need in self.providers[n].capabilities]
        if not capable:
            raise CapabilityError(f"Ningún cerebro para '{task}' entiende '{need}'")
        return capable

    def can(self, task: str, need: str, *, private: bool = False, local_only: bool = False) -> bool:
        """¿Hay ruta nativa para `need`? Con `local_only`, solo cuenta si TODOS los cerebros de
        la ruta (respaldo incluido) son locales."""
        try:
            names = self.order(task, private=private, need=need)
        except ProviderError:
            return False
        return not local_only or all(self._is_local(n) for n in names)

    def _order(self, task: str, *, private: bool) -> list[str]:
        names = [self.routes.get(task, self.routes["chat"])]
        if self.fallback and self.fallback not in names:
            names.append(self.fallback)
        if not private:
            return names  # Con local_only, enforce_local() ya dejó solo locales
        # Lo privado: primero el proveedor privado, después los locales de la ruta normal
        local = [n for n in dict.fromkeys([self.private, *names]) if self._is_local(n)]
        if not local:
            raise PrivacyError("Petición privada y no hay ningún proveedor local disponible")
        return local

    def _is_local(self, name: str) -> bool:
        provider = self.providers.get(name)
        return provider is not None and provider.local

    def health_targets(self) -> list[str]:
        return list(dict.fromkeys([self.routes["chat"], self.routes["vision"]]))

    def describe(self) -> str:
        roles = {
            "chat": self.routes["chat"],
            "visión": self.routes["vision"],
            "documentos": self.routes["document"],
            "respaldo": self.fallback,
            "privado": self.private if self._is_local(self.private) else None,
        }
        return " · ".join(
            f"{role}={name} ({self.providers[name].model})"
            for role, name in roles.items()
            if name and name in self.providers
        )
