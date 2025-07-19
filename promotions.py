# promotions.py

"""
✨ promotions.py
Módulo para envíos de promociones y gestión de opt-in/out con emojis y texto claro.
"""

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, KeyboardButton

from database import Database
from config import ADMIN_ID
from reply import main_menu, options_menu, send_promo_menu, promo_toggle_menu

# Instancia de la base de datos
db = Database()

class PromoStates(StatesGroup):
    waiting_text = State()

def register_handlers_promotions(dp):
    @dp.message_handler(lambda m: m.text == "⚙️ Opciones")
    async def cmd_options(m: types.Message):
        """⚙️ Muestra el menú de opciones; el admin ve el botón de promociones."""
        kb = options_menu
        if m.from_user.id == ADMIN_ID:
            kb.add(KeyboardButton("📢 Enviar promoción a todos"))
        await m.answer("⚙️ Elige una opción:", reply_markup=kb)

    @dp.message_handler(
        lambda m: m.text == "📢 Enviar promoción a todos" and m.from_user.id == ADMIN_ID
    )
    async def cmd_start_promo(m: types.Message):
        """📢 Inicia el flujo para crear una promoción."""
        await m.answer("📢 Escribe el texto de la promoción:", reply_markup=ReplyKeyboardRemove())
        await PromoStates.waiting_text.set()

    @dp.message_handler(state=PromoStates.waiting_text)
    async def process_promo_text(m: types.Message, state: FSMContext):
        """🚀 Envía la promoción a todos los usuarios que la tienen activada."""
        text = m.text
        rows = db.conn.execute(
            "SELECT telegram_id FROM users WHERE receive_promos = 1"
        ).fetchall()
        sent = 0
        for row in rows:
            try:
                await m.bot.send_message(
                    row["telegram_id"],
                    f"📣 *Promoción Especial* 📣\n\n{text}",
                    parse_mode=types.ParseMode.MARKDOWN
                )
                sent += 1
            except:
                pass
        await m.answer(f"✅ Promoción enviada a {sent} usuarios.", reply_markup=main_menu)
        await state.finish()

    @dp.message_handler(lambda m: m.text in ["🔔 Activar promos", "🔕 Desactivar promos"])
    async def cmd_toggle_promos(m: types.Message):
        """🔔 Permite a usuarios premium activar o desactivar promociones."""
        user = db.get_user(m.from_user.id)
        if not user or not user["is_premium"]:
            await m.answer("🔒 Solo usuarios Premium pueden gestionar promociones.", reply_markup=main_menu)
            return
        enable = m.text == "🔔 Activar promos"
        db.toggle_promo(m.from_user.id, enable)
        resp = "🔔 ¡Promociones activadas!" if enable else "🔕 Promociones desactivadas."
        await m.answer(resp, reply_markup=main_menu)
