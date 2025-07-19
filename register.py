# register.py

"""
✨ register.py
Módulo para el flujo de registro de usuarios en LeoMatch,
con mensajes enriquecidos y teclados bajo el teclado.
"""

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton

from database import Database
from reply import main_menu

# Instancia de base de datos
db = Database()

class RegisterStates(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_gender = State()
    waiting_bio = State()
    waiting_location = State()

def register_handlers_register(dp):
    @dp.message_handler(commands=['start'], state='*')
    async def cmd_start(message: types.Message, state: FSMContext):
        """👋 Inicia o retoma el registro del usuario."""
        user = db.get_user(message.from_user.id)
        if user:
            await message.answer(
                "👋 ¡Hola de nuevo! Ya estás registrado. Usa el menú para navegar.",
                reply_markup=main_menu
            )
            return
        # Añadimos al usuario con nombre provisional
        db.add_user(message.from_user.id, message.from_user.full_name)
        await message.answer(
            "🎉 ¡Bienvenido a LeoMatch! 💕\n\n"
            "Para comenzar, dime tu nombre o apodo:",
            reply_markup=ReplyKeyboardRemove()
        )
        await RegisterStates.waiting_name.set()

    @dp.message_handler(state=RegisterStates.waiting_name)
    async def process_name(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text.strip())
        await message.answer(
            "📅 ¿Cuántos años tienes? Por favor envía un número.",
            reply_markup=ReplyKeyboardRemove()
        )
        await RegisterStates.waiting_age.set()

    @dp.message_handler(lambda m: not m.text.isdigit(), state=RegisterStates.waiting_age)
    async def process_age_invalid(message: types.Message):
        await message.answer("❌ Edad no válida. Ingresa tu edad en números.")

    @dp.message_handler(lambda m: m.text.isdigit(), state=RegisterStates.waiting_age)
    async def process_age(message: types.Message, state: FSMContext):
        age = int(message.text)
        if age < 18:
            await message.answer("🔞 Debes ser mayor de edad para usar este bot.")
            return
        await state.update_data(age=age)
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(KeyboardButton("Hombre"), KeyboardButton("Mujer"), KeyboardButton("Otro"))
        await message.answer(
            "⚧️ Selecciona tu género:",
            reply_markup=kb
        )
        await RegisterStates.waiting_gender.set()

    @dp.message_handler(lambda m: m.text not in ["Hombre", "Mujer", "Otro"], state=RegisterStates.waiting_gender)
    async def process_gender_invalid(message: types.Message):
        await message.answer("❌ Opción no válida. Usa los botones del teclado.")

    @dp.message_handler(state=RegisterStates.waiting_gender)
    async def process_gender(message: types.Message, state: FSMContext):
        await state.update_data(gender=message.text)
        await message.answer(
            "📝 Cuéntame algo sobre ti (tu bio):",
            reply_markup=ReplyKeyboardRemove()
        )
        await RegisterStates.waiting_bio.set()

    @dp.message_handler(state=RegisterStates.waiting_bio)
    async def process_bio(message: types.Message, state: FSMContext):
        await state.update_data(bio=message.text.strip())
        await message.answer(
            "📍 ¿En qué ciudad o país vives? Ej: Madrid, España",
            reply_markup=ReplyKeyboardRemove()
        )
        await RegisterStates.waiting_location.set()

    @dp.message_handler(state=RegisterStates.waiting_location)
    async def process_location(message: types.Message, state: FSMContext):
        await state.update_data(location=message.text.strip())
        data = await state.get_data()
        # Actualizamos todos los campos en la BD
        db.update_user(
            telegram_id=message.from_user.id,
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            bio=data['bio'],
            location=data['location']
        )
        await message.answer(
            "✅ ¡Registro completo! 🎉\n\n"
            "🔍 Usa «🔍 Buscar personas» para encontrar tu match.\n"
            "💬 Usa «💬 Mis matches» para ver tus conexiones.\n"
            "✏️ Usa «✏️ Editar perfil» para actualizar tu información.\n\n"
            "¡Disfruta y suerte en tus matches! 💕",
            reply_markup=main_menu
        )
        await state.finish()
