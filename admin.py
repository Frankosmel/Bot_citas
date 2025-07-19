# admin.py

"""
✨ admin.py
Módulo para panel de administración: listado de usuarios y acciones básicas.
"""

from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database import Database
from config import ADMIN_ID
from reply import main_menu

# Instancia de la base de datos
db = Database()

def register_handlers_admin(dp):
    @dp.message_handler(commands=['admin'])
    async def cmd_admin(m: types.Message):
        """👑 Muestra el panel de administrador (solo para ADMIN_ID)."""
        if m.from_user.id != ADMIN_ID:
            await m.answer("❌ No tienes permisos para usar este comando.", reply_markup=main_menu)
            return

        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(KeyboardButton("📋 Ver usuarios"))
        kb.add(KeyboardButton("❌ Salir"))
        await m.answer("👑 Panel de administración:\nElige una opción:", reply_markup=kb)

    @dp.message_handler(lambda m: m.text == "📋 Ver usuarios")
    async def cmd_view_users(m: types.Message):
        """👥 Envía la lista de usuarios registrados con su estado Premium/Free."""
        if m.from_user.id != ADMIN_ID:
            await m.answer("❌ Permiso denegado.", reply_markup=main_menu)
            return

        rows = db.conn.execute("SELECT telegram_id, name, is_premium FROM users").fetchall()
        if not rows:
            await m.answer("🚫 No hay usuarios registrados.", reply_markup=main_menu)
            return

        text = "👥 *Usuarios registrados*:\n\n"
        for u in rows:
            status = "Premium" if u["is_premium"] else "Free"
            text += f"• {u['name']} ({u['telegram_id']}): _{status}_\n"
        await m.answer(text, parse_mode=types.ParseMode.MARKDOWN, reply_markup=main_menu)

    @dp.message_handler(lambda m: m.text == "❌ Salir")
    async def cmd_admin_exit(m: types.Message):
        """❌ Cierra el panel y regresa al menú principal."""
        await m.answer("🔙 Volviendo al menú principal.", reply_markup=main_menu)
