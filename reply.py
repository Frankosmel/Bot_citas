# reply.py

"""
✨ reply.py
Define los teclados principales bajo el teclado para LeoMatch.
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 🏠 Teclado principal para usuarios
main_menu = ReplyKeyboardMarkup(
    resize_keyboard=True,
    one_time_keyboard=False
)
main_menu.add(
    KeyboardButton("🔍 Buscar personas"),
    KeyboardButton("💬 Mis matches")
).add(
    KeyboardButton("✏️ Editar perfil"),
    KeyboardButton("💎 Suscribirse Premium")
).add(
    KeyboardButton("🚫 Bloquear usuario"),
    KeyboardButton("⚙️ Opciones")
)

# ⚙️ Menú de opciones generales (perfil, ayuda)
options_menu = ReplyKeyboardMarkup(resize_keyboard=True)
options_menu.add(
    KeyboardButton("🌐 Cambiar ubicación"),
    KeyboardButton("❓ Ayuda")
)

# 📢 Teclado para envío de promociones (solo para el admin)
send_promo_menu = ReplyKeyboardMarkup(resize_keyboard=True)
send_promo_menu.add(
    KeyboardButton("📢 Enviar promoción a todos")
)

# 🔔 Teclado para usuarios premium gestionar promociones
promo_toggle_menu = ReplyKeyboardMarkup(resize_keyboard=True)
promo_toggle_menu.add(
    KeyboardButton("🔔 Activar promos"),
    KeyboardButton("🔕 Desactivar promos")
)
