---
description: Guía paso a paso para subir el repositorio a GitHub de forma segura.
---

# Subir Repositorio a GitHub

Sigue estos pasos para subir tu proyecto a GitHub asegurando que no se filtre información sensible.

## 1. Verificar Archivos Ignorados

Asegúrate de que `git` ignore los archivos sensibles antes de añadir nada.

```powershell
# Verificar que .env está siendo ignorado
Get-Content .gitignore
# Debería mostrar .env en la lista
```

## 2. Inicializar y Configurar Git (si es nuevo)

Si aún no has inicializado el repositorio:

```powershell
git init
git branch -M main
```

## 3. Añadir Archivos

Añade los archivos al área de preparación (staging).

```powershell
git add .
```

Verifica qué se va a subir:

```powershell
git status
```

**IMPORTANTE**: Revisa la lista. NO debe aparecer `.env`, `__pycache__`, ni carpetas `venv`. Si aparecen, edita el `.gitignore` y usa `git rm --cached <archivo>` para quitarlos.

### Paso Crítico: Eliminar Archivos Sensibles del Historial
Si `.env` ya estaba siendo rastreado por git anteriormente (aparece en `git status` sin ser "untracked"), debes dejar de rastrearlo sin borrar el archivo de tu disco:

```powershell
git rm --cached .env
```
Esto asegurará que tu token NO se suba al repositorio público en el siguiente commit.


## 4. Crear el Commit

Realiza el commit con un mensaje descriptivo.

```powershell
git commit -m "feat: Initial commit - Telegram Bot with Marin Kitagawa persona"
```

## 5. Subir a GitHub

Crea un nuevo repositorio vacío en GitHub (sin README, ni .gitignore, ni licencia, ya los tenemos localmente).
Copia la URL del repositorio (ej: `https://github.com/usuario/repo.git`).

Vincula el repositorio remoto:

```powershell
git remote add origin <URL_DEL_REPOSITORIO>
# Si ya existe origin, usa: git remote set-url origin <URL_DEL_REPOSITORIO>
```

Sube los cambios:

```powershell
git push -u origin main
```

## Solución de Problemas Comunes

*   **Error: "fatal: remote origin already exists"**:
    Usa `git remote set-url origin <NUEVA_URL>` para corregirlo.

*   **Error: "refusing to merge unrelated histories"**:
    Si creaste el repo en GitHub con un README, usa: `git pull origin main --allow-unrelated-histories` antes de hacer push.

*   **Verificar Seguridad**:
    Siempre revisa `git status` antes de hacer commit para asegurarte de que no estás subiendo claves API.
