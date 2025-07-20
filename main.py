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

# Estados de conversación
PROFILE_CHOICE = 0
DESC, INSTA, GENDER, COUNTRY, CITY = range(1, 6)
MATCH = 0

# Teclados
def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["👥 Emparejar", "🔔 Promociones"],
        ["📄 Perfil",     "🛑 Salir"]
    ], resize_keyboard=True)

def profile_menu_keyboard(has_profile: bool) -> ReplyKeyboardMarkup:
    buttons = []
    if not has_profile:
        buttons.append([KeyboardButton("🆕 Crear Perfil")])
    else:
        buttons.append([KeyboardButton("✏️ Editar Perfil")])
        buttons.append([KeyboardButton("🗑️ Eliminar Perfil")])
    buttons.append([KeyboardButton("🏠 Volver")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def match_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["❤️ Me gusta", "🚫 No me gusta"],
        ["🏠 Menú"]
    ], resize_keyboard=True)

# — Handlers —

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    await update.message.reply_text(
        "Leo: ¡Ligar. Citas y amigos! 💕\n"
        "Contacto 👉 @frankosmel\n\n"
        f"¡Hola, {user.first_name}! 🤖\n"
        "Elige una opción:",
        reply_markup=main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usa los botones para navegar.\n"
        "Envía /cancelar para salir de un flujo."
    )

# Fallback principal
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "👥 Emparejar":
        return await match_start(update, context)

    if text == "🔔 Promociones":
        is_prem = db.is_premium(user_id)
        await update.message.reply_text(
            "Para recibir promos hazte Premium 💎" if not is_prem else "No hay promos nuevas 🤝",
            reply_markup=main_keyboard()
        )
        return

    if text == "📄 Perfil":
        has = db.has_profile(user_id)
        await update.message.reply_text(
            "Gestión de Perfil:",
            reply_markup=profile_menu_keyboard(has)
        )
        return PROFILE_CHOICE

    if text == "🛑 Salir":
        db.unregister_user(user_id)
        await update.message.reply_text(
            "Has salido. Usa /start para volver. 👋",
            reply_markup=main_keyboard()
        )
        return

    # Texto desconocido
    await update.message.reply_text(
        "Opción no válida. Usa los botones.",
        reply_markup=main_keyboard()
    )

# — Perfil: menú —
async def profile_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if text == "🆕 Crear Perfil":
        await update.message.reply_text("📝 Envíame una descripción de tu perfil:")
        return DESC

    if text == "✏️ Editar Perfil":
        p = db.get_profile(uid)
        await update.message.reply_text(
            f"Tu perfil actual:\n"
            f"📝 {p.description}\n"
            f"📸 instagram.com/{p.instagram}\n"
            f"👤 {p.gender}\n"
            f"📍 {p.city}, {p.country}\n\n"
            "Envía la nueva descripción:"
        )
        return DESC

    if text == "🗑️ Eliminar Perfil":
        db.delete_profile(uid)
        await update.message.reply_text(
            "✅ Perfil eliminado.\nVolviendo al menú principal.",
            reply_markup=main_keyboard()
        )
        return ConversationHandler.END

    if text == "🏠 Volver":
        await update.message.reply_text(
            "Menú principal:",
            reply_markup=main_keyboard()
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Opción inválida.",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END

# — Perfil: pasos —
async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("📸 Tu usuario de Instagram (sin @):")
    return INSTA

async def perfil_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['instagram'] = update.message.text
    await update.message.reply_text("👤 Tu género (Masculino/Femenino/Otro):")
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
    uid = update.effective_user.id
    db.save_profile(
        uid,
        description=context.user_data['description'],
        instagram=context.user_data['instagram'],
        gender=context.user_data['gender'],
        country=context.user_data['country'],
        city=update.message.text
    )
    await update.message.reply_text(
        "✅ Perfil creado/actualizado correctamente.",
        reply_markup=main_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END

# — Emparejar flow —
async def match_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    context.user_data['candidates'] = db.get_potential_matches(uid)
    context.user_data['idx'] = 0
    if not context.user_data['candidates']:
        await update.message.reply_text("No hay perfiles cercanos.", reply_markup=main_keyboard())
        return ConversationHandler.END
    return await show_next_profile(update, context)

async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]
    text = (
        f"👤 {cand.fullname}\n"
        f"📍 {cand.city}, {cand.country}\n"
        f"📸 instagram.com/{cand.instagram}\n\n"
        f"{cand.description}"
    )
    await update.message.reply_text(text, reply_markup=match_keyboard())
    return MATCH

async def match_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    uid = update.effective_user.id
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]

    if choice == "❤️ Me gusta":
        if db.record_like(uid, cand.id):
            await update.message.reply_text(
                f"🎉 ¡Match con @{cand.username}! Ahora podéis escribiros en privado.",
                reply_markup=main_keyboard()
            )
            return ConversationHandler.END

    if choice == "🚫 No me gusta":
        context.user_data['idx'] += 1
        return await show_next_profile(update, context)

    await update.message.reply_text("Volviendo al menú principal.", reply_markup=main_keyboard())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Operación cancelada.", reply_markup=main_keyboard())
    return ConversationHandler.END

# — Lanzamiento —
if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Perfil
    perfil_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^📄 Perfil$"), handle_message)],
        states={
            PROFILE_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_choice)],
            DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_description)],
            INSTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_instagram)],
            GENDER:[MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_gender)],
            COUNTRY:[MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_country)],
            CITY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_city)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    app.add_handler(perfil_conv)

    # Emparejar
    match_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^👥 Emparejar$"), match_start)],
        states={ MATCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, match_choice)] },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    app.add_handler(match_conv)

    # Fallback general
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot iniciado con todos los flujos")
    app.run_polling(drop_pending_updates=True)
