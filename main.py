# main.py

import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import config
from database import Database

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

db = Database(config.DB_URL)

# Conversation states
DESC, INSTA, GENDER, COUNTRY, CITY = range(5)
MATCH = 0

# Keyboards
def main_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton("👥 Emparejar"), KeyboardButton("🔔 Promociones")],
        [KeyboardButton("📄 Perfil"),     KeyboardButton("🛑 Salir")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def match_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton("👍 Me gusta"), KeyboardButton("➡️ Siguiente")],
        [KeyboardButton("🏠 Menú")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# —————————————————————
# Handlers de comandos
# —————————————————————

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    text = (
        "Leo: ¡Ligar. Citas y amigos! 💕\n"
        "Ayuda 👉 @leomatchbot_help\n"
        "Compra publicidad 👉 @ADinsidebot\n\n"
        f"¡Hola, {user.first_name}! 🤖\n"
        "Bienvenido a LeoMatch Bot. Elige una opción:"
    )
    await update.message.reply_text(text, reply_markup=main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usa los botones del teclado para navegar.\n"
        "Para cancelar un flujo, envía /cancelar."
    )

# —————————————————————
# Handler general de texto (fallback al menú principal)
# —————————————————————

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # Emparejar
    if text == "👥 Emparejar":
        return await match_start(update, context)

    # Promociones
    if text == "🔔 Promociones":
        is_prem = db.is_premium(user_id)
        reply = (
            "Para recibir promociones, hazte Premium 💎"
            if not is_prem else "No hay promociones nuevas 🤝"
        )
        await update.message.reply_text(reply, reply_markup=main_keyboard())
        return

    # Perfil
    if text == "📄 Perfil":
        return await perfil_start(update, context)

    # Salir
    if text == "🛑 Salir":
        db.unregister_user(user_id)
        await update.message.reply_text("Has salido. Usa /start para volver. 👋",
                                        reply_markup=main_keyboard())
        return

    # Cualquier otro texto
    await update.message.reply_text("Opción no válida. Usa los botones.",
                                    reply_markup=main_keyboard())

# —————————————————————
# Flujo de Emparejar
# —————————————————————

async def match_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['candidates'] = db.get_potential_matches(user_id)
    context.user_data['idx'] = 0
    if not context.user_data['candidates']:
        await update.message.reply_text(
            "No hay usuarios cerca en este momento.",
            reply_markup=main_keyboard()
        )
        return ConversationHandler.END
    return await show_next_profile(update, context)

async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['idx']
    candidates = context.user_data['candidates']
    if idx >= len(candidates):
        await update.message.reply_text(
            "Has llegado al final de la lista.",
            reply_markup=main_keyboard()
        )
        return ConversationHandler.END
    user = candidates[idx]
    text = (
        f"👤 {user.fullname}\n"
        f"📍 {user.city}, {user.country}\n"
        f"Instagram: https://instagram.com/{user.instagram}\n\n"
        "¿Te gusta este perfil?"
    )
    await update.message.reply_text(text, reply_markup=match_keyboard())
    return MATCH

async def match_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    user_id = update.effective_user.id
    idx = context.user_data['idx']
    candidates = context.user_data['candidates']
    current = candidates[idx]

    if choice == "👍 Me gusta":
        if db.record_like(user_id, current.id):
            await update.message.reply_text(
                "¡Es un match! Ahora podéis hablar por privado:\n"
                f"@{current.username} & @{update.effective_user.username}",
                reply_markup=main_keyboard()
            )
            return ConversationHandler.END

    if choice == "➡️ Siguiente":
        context.user_data['idx'] += 1
        return await show_next_profile(update, context)

    # Menú
    await update.message.reply_text("Volviendo al menú principal.",
                                    reply_markup=main_keyboard())
    return ConversationHandler.END

# —————————————————————
# Flujo de Perfil
# —————————————————————

async def perfil_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Envía tu descripción de perfil (o /cancelar):")
    return DESC

async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("📸 Envía tu usuario de Instagram (sin @):")
    return INSTA

async def perfil_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['instagram'] = update.message.text
    await update.message.reply_text("👤 Selecciona tu género: Masculino/Femenino/Otro")
    return GENDER

async def perfil_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("🌍 ¿En qué país vives?")
    return COUNTRY

async def perfil_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['country'] = update.message.text
    await update.message.reply_text("🏙️ ¿Ciudad o provincia?")
    return CITY

async def perfil_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    db.update_profile(
        update.effective_user.id,
        context.user_data['description'],
        context.user_data['instagram'],
        context.user_data['gender'],
        context.user_data['country'],
        context.user_data['city']
    )
    summary = (
        "✅ Perfil actualizado!\n"
        f"📝 {context.user_data['description']}\n"
        f"📸 instagram.com/{context.user_data['instagram']}\n"
        f"👤 {context.user_data['gender']}\n"
        f"📍 {context.user_data['city']}, {context.user_data['country']}"
    )
    context.user_data.clear()
    await update.message.reply_text(summary, reply_markup=main_keyboard())
    return ConversationHandler.END

async def perfil_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Edición de perfil cancelada.", reply_markup=main_keyboard())
    return ConversationHandler.END

# —————————————————————
# Arranque de la App
# —————————————————————

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Conversación Emparejar
    match_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^👥 Emparejar$"), match_start)],
        states={ MATCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, match_choice)] },
        fallbacks=[CommandHandler("cancelar", perfil_cancel)],
    )
    app.add_handler(match_conv)

    # Conversación Perfil
    perfil_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📄 Perfil$"), perfil_start)],
        states={
            DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_description)],
            INSTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_instagram)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_gender)],
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_country)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_city)],
        },
        fallbacks=[CommandHandler("cancelar", perfil_cancel)],
    )
    app.add_handler(perfil_conv)

    # Fallback teclado principal
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot iniciado con flujos de Emparejar y Perfil")
    app.run_polling()
