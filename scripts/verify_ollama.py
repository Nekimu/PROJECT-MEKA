"""Diagnóstico de Ollama: conexión, modelo instalado y una respuesta de prueba.

Uso (desde la raíz del proyecto):  python -m scripts.verify_ollama
"""

from colorama import Fore, init
from ollama import Client

from core.config import settings

init(autoreset=True)


def verify_ollama():
    ai_config = settings.get("ai", {})
    model_name = ai_config.get("model", "gemma3:12b")
    base_url = ai_config.get("base_url", "http://localhost:11434")
    client = Client(host=base_url)

    print(f"{Fore.CYAN}--- Verificando conexión con Ollama ---")
    print(f"URL: {base_url}")
    print(f"Modelo objetivo: {model_name}")

    try:
        print(f"\n{Fore.YELLOW}Consultando lista de modelos instalados...")
        models = [m.model for m in client.list().models]
    except Exception as e:
        print(f"{Fore.RED}❌ Error conectando con Ollama: {e}")
        print(f"{Fore.YELLOW}Asegúrate de que Ollama esté ejecutándose (`ollama serve`).")
        return

    print(f"{Fore.GREEN}Conexión exitosa. Modelos encontrados: {len(models)}")
    for m in models:
        print(f" - {m}")

    # Ollama añade ":latest" si el nombre no lleva etiqueta
    wanted = model_name if ":" in model_name else f"{model_name}:latest"
    if wanted in models:
        print(f"\n{Fore.GREEN}✅ El modelo '{model_name}' está instalado.")
    else:
        print(f"\n{Fore.RED}❌ El modelo '{model_name}' NO se encontró en la lista.")
        print(f"{Fore.YELLOW}Intentando descargar (pull) '{model_name}'... Esto puede tardar.")
        try:
            for progress in client.pull(model_name, stream=True):
                if progress.total:
                    percent = (progress.completed or 0) / progress.total * 100
                    print(f"\r Descargando: {progress.status} - {percent:.1f}%", end="")
                else:
                    print(f"\r Descargando: {progress.status}", end="")
            print(f"\n{Fore.GREEN}✅ Descarga completada.")
        except Exception as e:
            print(f"\n{Fore.RED}Error al descargar el modelo: {e}")
            return

    print(f"\n{Fore.YELLOW}Probando generación de respuesta simple...")
    try:
        response = client.chat(
            model=model_name,
            messages=[{"role": "user", "content": 'Di "Hola Marin" si me escuchas.'}],
            keep_alive=0,
        )
        print(f"{Fore.GREEN}✅ Respuesta de {model_name}:")
        print(f"{Fore.MAGENTA}{response.message.content}")
    except Exception as e:
        print(f"{Fore.RED}Error generando respuesta: {e}")


if __name__ == "__main__":
    verify_ollama()
