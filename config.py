# config.py
import os

# 🚀 Token de tu bot (pon tu token real o define la variable de entorno TELEGRAM_TOKEN)
API_TOKEN = os.getenv("TELEGRAM_TOKEN", "7620871456:AAHZHfLOimiMQyZ2vT-oWwNzIUpM3zqANPU")

# 👑 ID de administrador (solo él podrá enviar promociones y gestionar usuarios)
ADMIN_ID = int(os.getenv("ADMIN_ID", "1383931339"))

# 📂 Nombres de archivos de base de datos y esquema
DB_FILENAME = "users.db"       # Archivo SQLite donde se guardan los datos
SCHEMA_FILENAME = "models.sql" # Script SQL para crear las tablas

# 🆓 Opciones disponibles para usuarios GRATUITOS
# - 'todos': empareja con cualquier usuario (hombre o mujer)
FREE_CHOICES = ["todos"]

# 💎 Opciones adicionales para usuarios PREMIUM
# - 'hombres': solo empareja con hombres
# - 'mujeres': solo empareja con mujeres
PREMIUM_CHOICES = ["hombres", "mujeres"]

# 🎉 Mensajes estándar (puedes importarlos en tus handlers)
WELCOME_TEXT = (
    "🎉 ¡Bienvenido a LeoMatch! 💕

"
    "Para empezar, usa el comando /start y sigue los pasos de registro."
)
ALREADY_REGISTERED_TEXT = "👋 ¡Ya estás registrado! Usa el menú para navegar."
```python
import os

API_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1383931339"))  # Reemplaza si es necesario

# Opciones disponibles para usuarios gratuitos
FREE_CHOICES = ["todos"]
# Opciones adicionales para premium
PREMIUM_CHOICES = ["hombres", "mujeres"]
