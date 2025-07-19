# profile.py

"""
✨ profile.py
Módulo para ver y editar perfil de usuario en LeoMatch,
con mensajes enriquecidos, emojis y teclados bajo el teclado.
"""

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ParseMode

from database import Database
from reply import main_menu

# Instancia de base de datos
db = Database()

class EditProfileStates(StatesGroup):
    choosing_field = State()
    updating_value = State()

def register_handlers_profile(dp):
    @dp.message_handler(lambda m: m.text == "✏️ Editar perfil")
    async def cmd_edit_profile(m: types.Message):
        """👤 Muestra tu perfil actual y opciones para editar."""
        user = db.get_user(m.from_user.id)
        if not user:
            await m.answer("❌ Primero regístrate con /start.", reply_markup=main_menu)
            return

        text = (
            f"👤 *Tu perfil* 👤\n\n"
            f"• *Nombre:* {user['name']}\n"
            f"• *Edad:* {user['age']}\n"
            f"• *Género:* {user['gender'].capitalize()}\n"
            f"• *Bio:* {user['bio'] or 'Sin descripción'}\n"
            f"• *Ubicación:* {user['location'] or 'No especificada'}\n\n"
            "¿Qué deseas editar?"
        )
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(
            KeyboardButton("🖊️ Nombre"), KeyboardButton("🎂 Edad")
        ).add(
            KeyboardButton("⚧️ Género"), KeyboardButton("📝 Bio")
        ).add(
            KeyboardButton("📍 Ubicación"), KeyboardButton("❌ Cancelar")
        )
        await m.answer(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        await EditProfileStates.choosing_field.set()

    @dp.message_handler(lambda m: m.text == "❌ Cancelar", state=EditProfileStates.choosing_field)
    async def cancel_edit(m: types.Message, state: FSMContext):
        """❌ Cancela la edición de perfil."""
        await state.finish()
        await m.answer("❌ Edición cancelada.", reply_markup=main_menu)

    @dp.message_handler(state=EditProfileStates.choosing_field)
    async def choose_field(m: types.Message, state: FSMContext):
        field_map = {
            "🖊️ Nombre": "name",
            "🎂 Edad": "age",
            "⚧️ Género": "gender",
            "📝 Bio": "bio",
            "📍 Ubicación": "location"
        }
        choice = m.text
        if choice not in field_map:
            await m.answer("❌ Opción no válida. Usa los botones del teclado.", reply_markup=main_menu)
            await state.finish()
            return

        await state.update_data(field=field_map[choice])
        prompts = {
            "name": "🖊️ Ingresa tu nuevo nombre o apodo:",
            "age": "🎂 Ingresa tu nueva edad (número):",
            "gender": "⚧️ Ingresa tu género (Hombre/Mujer/Otro):",
            "bio": "📝 Escribe tu nueva bio:",
            "location": "📍 Escribe tu nueva ubicación:"
        }
        await m.answer(prompts[field_map[choice]], reply_markup=ReplyKeyboardRemove())
        await EditProfileStates.updating_value.set()

    @dp.message_handler(state=EditProfileStates.updating_value)
    async def update_value(m: types.Message, state: FSMContext):
        data = await state.get_data()
        field = data['field']
        value = m.text.strip()

        # Validaciones específicas
        if field == "age":
            if not value.isdigit():
                await m.answer("❌ Ingresa un número válido para la edad.")
                return
            value = int(value)
        if field == "gender":
            if value.lower() not in ["hombre", "mujer", "otro"]:
                await m.answer("❌ Ingresa: Hombre, Mujer u Otro.")
                return
            value = value.capitalize()

        # Actualizar en la base de datos
        db.update_user(m.from_user.id, **{field: value})
        await m.answer(f"✅ *{field.capitalize()}* actualizado con éxito.", 
                       reply_markup=main_menu, parse_mode=ParseMode.MARKDOWN)
        await state.finish()
