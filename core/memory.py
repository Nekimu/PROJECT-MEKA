import json
import os
from core.logger import setup_logger

logger = setup_logger("Memory_System")

class MemorySystem:
    def __init__(self, file_path="memory.json"):
        self.file_path = file_path
        self.data = self._load()

    def _load(self):
        """Carga la memoria desde el archivo JSON."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando memoria: {e}")
                return {"facts": []}
        return {"facts": []}

    def _save(self):
        """Guarda la memoria en el archivo JSON."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando memoria: {e}")

    def add_fact(self, fact: str):
        """Añade un hecho a la memoria."""
        if fact not in self.data["facts"]:
            self.data["facts"].append(fact)
            self._save()
            logger.info(f"Nuevo hecho recordado: {fact}")
            return True
        return False

    def get_all_memories(self):
        """Devuelve todos los hechos recordados."""
        return self.data["facts"]

    def search_memories(self, query: str):
        """Busca hechos relevantes basados en palabras clave."""
        query = query.lower()
        # Palabras a ignorar en la búsqueda (conectores y disparadores)
        ignore = ["recuerdas", "acuerdas", "sabes", "dijiste", "sobre", "esto", "esta", "donde"]
        
        # Búsqueda simple por palabras clave
        keywords = [word for word in query.split() if len(word) > 3 and word not in ignore]
        results = []
        
        if not keywords:
            # Si no hay palabras clave claras, devolver los últimos recuerdos
            return self.data["facts"][-5:]

        for fact in self.data["facts"]:
            if any(kw in fact.lower() for kw in keywords):
                results.append(fact)
        
        return results if results else self.data["facts"][-3:]

# Instancia global
memory_system = MemorySystem()
