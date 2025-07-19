# match.py

"""
✨ match.py
Módulo para búsqueda de perfiles, mostrar detalles y gestionar “Me gusta”/“Pasar”
con botones inline y mensajes enriquecidos.
"""

import json
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from reply import main_menu

# Instancia de la base de datos
db = Database()

def register_handlers_match(dp):
    @dp.message_handler(lambda m: m.text == "🔍 Buscar personas")
    async def cmd_search(m: types.Message):
        """🔍 Busca y muestra el siguiente perfil según tu preferencia."""
        user = db.get_user(m.from_user.id)
        if not user:
            await m.answer("❌ Primero regístrate con /start.", reply_markup=main_menu)
            return

        # Construir filtros básicos
        filters = ["telegram_id != ?"]
        params = [m.from_user.id]

        # Excluir ya vistos (likes y matches)
        liked = json.loads(user["liked_users"])
        matched = json.loads(user["matched_users"])
        excluded = liked + matched + [m.from_user.id]
        filters.append("telegram_id NOT IN ({})".format(",".join("?"*len(excluded))))
        params.extend(excluded)

        # Si eres premium y elegiste un género, aplicamos filtro
        if user["is_premium"] and user["looking_for"] != "todos":
            filters.append("gender = ?")
            # mapping: looking_for almacena "hombres"/"mujeres"
            target_gender = "hombre" if user["looking_for"] == "hombres" else "mujer"
            params.append(target_gender)

        sql = f"SELECT * FROM users WHERE {' AND '.join(filters)} LIMIT 1"
        row = db.conn.execute(sql, params).fetchone()
        if not row:
            await m.answer("😔 No hay más perfiles por ahora. Vuelve más tarde.", reply_markup=main_menu)
            return

        profile = dict(row)
        # Formatear texto del perfil
        text = (
            f"👤 *{profile['name']}*, {profile['age']} años\n"
            f"⚧️ Género: {profile['gender'].capitalize()}\n"
            f"📍 {profile['location']}\n\n"
            f"💬 _{profile['bio'] or 'Sin descripción...'}_"
        )
        # Botones inline: Me gusta / Pasar
        kb = InlineKeyboardMarkup(row_width=2)
        kb.insert(InlineKeyboardButton("❤️ Me gusta", callback_data=f"like:{profile['telegram_id']}"))
        kb.insert(InlineKeyboardButton("❌ Pasar", callback_data=f"pass:{profile['telegram_id']}"))

        await m.answer(text, reply_markup=kb, parse_mode=types.ParseMode.MARKDOWN)

    @dp.callback_query_handler(lambda c: c.data and c.data.startswith("like:"))
    async def process_like(c: types.CallbackQuery):
        """❤️ Maneja el “Me gusta” y verifica match."""
        user_id = c.from_user.id
        target_id = int(c.data.split(":")[1])
        db.like_user(user_id, target_id)

        # Verificar si se produjo un match
        user = db.get_user(user_id)
        if target_id in json.loads(user["matched_users"]):
            await c.answer("🤝 ¡Es un match! Ahora pueden empezar a chatear.", show_alert=True)
        else:
            await c.answer("✅ Has dado Me gusta.", show_alert=False)

        # Invitar a seguir buscando
        await c.message.answer("🔍 Envía «🔍 Buscar personas» para seguir explorando.", reply_markup=main_menu)

    @dp.callback_query_handler(lambda c: c.data and c.data.startswith("pass:"))
    async def process_pass(c: types.CallbackQuery):
        """❌ Maneja el paso sin Me gusta."""
        await c.answer("✔️ Has pasado este perfil.", show_alert=False)
        await c.message.answer("🔍 Envía «🔍 Buscar personas» para seguir explorando.", reply_markup=main_menu)

# Para usar, en main.py haz:
# from match import register_handlers_match
# register_handlers_match(dp)
