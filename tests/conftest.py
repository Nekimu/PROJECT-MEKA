import os

# Valores de prueba para que importar los módulos no dependa del .env local
os.environ.setdefault("TELEGRAM_TOKEN", "123456:TEST-TOKEN")
os.environ.setdefault("ALLOWED_USER_IDS", "")
