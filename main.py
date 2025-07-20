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

# Database init
db = Database(config.DB_URL)

# Conversation states for profile editing
DESC, INSTA, GENDER, COUNTRY, CITY = range(5)

def main_keyboard(is_premium: bool = False, is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Four-button main keyboard: Pair, Promotions, Profile, Exit
    """
    buttons = [
        [KeyboardButton("👥 Emparejar"), KeyboardButton("🔔 Promociones")],
        [KeyboardButton("📄 Perfil"),   KeyboardButton("🛑 Salir")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    text = (
        f"¡Hola, {user.first_name}! 🤖\n"
        "Bienvenido a LeoMatch Bot. Elige una opción:"
    )
    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(),
    )

# /help handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usa los botones del teclado para navegar. Usa /cancelar para salir de un flujo. 🤖"
    )

# General message handler for the four main buttons
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "👥 Emparejar":
        is_prem = db.is_premium(user_id)
        matches = db.get_matches(version=is_prem)
        reply = "Tu lista de matches:\n" + "\n".join(matches) if matches else "No hay matches aún."

    elif text == "🔔 Promociones":
        is_prem = db.is_premium(user_id)
        reply = (
            "Para recibir promociones, hazte Premium 💎" if not is_prem
            else "No hay promociones nuevas 🤝"
        )

    elif text == "📄 Perfil":
        return await perfil_start(update, context)

    elif text == "🛑 Salir":
        db.unregister_user(user_id)
        reply = "Has salido. Usa /start para volver. 👋"

    else:
        reply = "Opción no válida. Usa los botones."

    await update.message.reply_text(
        reply,
        reply_markup=main_keyboard(),
    )

# --- Profile editing flow ---

async def perfil_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Enviar descripción de tu perfil (o /cancelar):")
    return DESC

async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("📸 Envía tu usuario de Instagram (sin @):")
    return INSTA

async def perfil_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['instagram'] = update.message.text
    await update.message.reply_text(
        "👤 Selecciona tu género:",
        reply_markup=ReplyKeyboardMarkup(
            [["Masculino"], ["Femenino"], ["Otro"], ["/cancelar"]],
            resize_keyboard=True
        )
    )
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
    # Save profile to DB
    db.update_profile(
        update.effective_user.id,
        context.user_data['description'],
        context.user_data['instagram'],
        context.user_data['gender'],
        context.user_data['country'],
        context.user_data['city'],
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
    await update.message.reply_text(
        "❌ Edición de perfil cancelada.",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END

# --- Main launch ---

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Profile conversation
    perfil_conv = ConversationHandler(
        entry_points=[CommandHandler("perfil", perfil_start)],
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

    # Main keyboard handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot iniciado con teclado simplificado y módulos de perfil")
    app.run_polling()
