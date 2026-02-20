import sys
import os
import yaml
import ollama
from colorama import init, Fore, Style

init(autoreset=True)

def load_config():
    try:
        with open("config.yml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"{Fore.RED}Error cargando config.yml: {e}")
        return {}

def verify_ollama():
    config = load_config()
    model_name = config.get("ai", {}).get("model", "llama3")
    base_url = config.get("ai", {}).get("base_url", "http://localhost:11434")

    print(f"{Fore.CYAN}--- Verificando conexión con Ollama ---")
    print(f"URL: {base_url}")
    print(f"Modelo objetivo: {model_name}")

    # Set base URL if needed (ollama python lib uses OLLAMA_HOST env var usually, or defaults to localhost)
    # The library connects to localhost:11434 by default.
    
    try:
        # Check list of models
        print(f"\n{Fore.YELLOW}Consultando lista de modelos instalados...")
        models_response = ollama.list()
        models = [m['model'] for m in models_response.get('models', [])]
        
        print(f"{Fore.GREEN}Conexión exitosa. Modelos encontrados: {len(models)}")
        for m in models:
            print(f" - {m}")

        # Verify specific model
        # Normalized names often have :latest inferred, checking partial match
        if any(model_name in m for m in models):
            print(f"\n{Fore.GREEN}✅ El modelo '{model_name}' está instalado.")
        else:
            print(f"\n{Fore.RED}❌ El modelo '{model_name}' NO se encontró en la lista.")
            print(f"{Fore.YELLOW}Intentando descargar (pull) '{model_name}'... Esto puede tardar.")
            try:
                # Streaming pull to show progress
                for progress in ollama.pull(model_name, stream=True):
                    status = progress.get('status', '')
                    completed = progress.get('completed', 0)
                    total = progress.get('total', 1)
                    if total:
                        percent = (completed / total) * 100
                        print(f"\r Descargando: {status} - {percent:.1f}%", end="")
                    else:
                        print(f"\r Descargando: {status}", end="")
                print(f"\n{Fore.GREEN}✅ Descarga completada.")
            except Exception as e:
                print(f"\n{Fore.RED}Error al descargar el modelo: {e}")
                return

        # Test generation
        print(f"\n{Fore.YELLOW}Probando generación de respuesta simple...")
        try:
            response = ollama.chat(model=model_name, messages=[
                {'role': 'user', 'content': 'Di "Hola Marin" si me escuchas.'}
            ])
            reply = response['message']['content']
            print(f"{Fore.GREEN}✅ Respuesta de {model_name}:")
            print(f"{Fore.MAGENTA}{reply}")
        except Exception as e:
            print(f"{Fore.RED}Error generando respuesta: {e}")

    except Exception as e:
        print(f"{Fore.RED}❌ Error conectando con Ollama: {e}")
        print(f"{Fore.YELLOW}Asegúrate de que Ollama esté ejecutándose (generalmente en el systray icon).")

if __name__ == "__main__":
    verify_ollama()
