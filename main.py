# main.py

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
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
PROFILE_MENU, PHOTO, DESC, INSTA, GENDER, COUNTRY, CITY = range(7)
MATCH = 0

# Keyboards
def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["👥 Emparejar", "🔔 Promociones"], ["📄 Perfil", "🛑 Salir"]],
        resize_keyboard=True
    )

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
    return ReplyKeyboardMarkup(
        [["❤️ Me gusta", "🚫 No me gusta"], ["🛑 Dejar Emparejar"]],
        resize_keyboard=True
    )

# /start
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

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usa los botones para navegar.\n"
        "Envía /cancelar para salir de cualquier flujo."
    )

# Fallback to main menu
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if text == "👥 Emparejar":
        return await match_start(update, context)

    if text == "🔔 Promociones":
        is_prem = db.is_premium(uid)
        await update.message.reply_text(
            "Para recibir promos hazte Premium 💎" if not is_prem else "No hay promos nuevas 🤝",
            reply_markup=main_keyboard()
        )
        return

    if text == "📄 Perfil":
        has = db.has_profile(uid)
        await update.message.reply_text(
            "Gestión de Perfil:",
            reply_markup=profile_menu_keyboard(has)
        )
        return PROFILE_MENU

    if text == "🛑 Salir":
        db.unregister_user(uid)
        await update.message.reply_text(
            "Has salido. Usa /start para volver. 👋",
            reply_markup=main_keyboard()
        )
        return

    await update.message.reply_text(
        "Opción no válida. Usa los botones.",
        reply_markup=main_keyboard()
    )

# Profile menu
async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if text in ("🆕 Crear Perfil", "✏️ Editar Perfil"):
        await update.message.reply_text("📷 Por favor, envía tu foto de perfil:")
        return PHOTO

    if text == "🗑️ Eliminar Perfil":
        db.delete_profile(uid)
        await update.message.reply_text("✅ Perfil eliminado.", reply_markup=main_keyboard())
        return ConversationHandler.END

    if text == "🏠 Volver":
        await update.message.reply_text("Menú principal:", reply_markup=main_keyboard())
        return ConversationHandler.END

    await update.message.reply_text("Opción inválida en Perfil.", reply_markup=main_keyboard())
    return ConversationHandler.END

# Profile creation/editing flow
async def perfil_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1].file_id
    context.user_data['photo'] = photo
    await update.message.reply_text("📝 Ahora envía una descripción breve:")
    return DESC

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
    await update.message.reply_text("🏙️ ¿Y ciudad o provincia?")
    return CITY

async def perfil_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db.save_profile(
        uid,
        context.user_data['photo'],
        context.user_data['description'],
        context.user_data['instagram'],
        context.user_data['gender'],
        context.user_data['country'],
        update.message.text
    )
    await update.message.reply_text("✅ Perfil guardado correctamente.", reply_markup=main_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# Match flow
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
    caption = (
        f"👤 {cand.fullname}\n"
        f"📍 {cand.city}, {cand.country}\n"
        f"📸 instagram.com/{cand.instagram}\n\n"
        f"{cand.description}"
    )
    await update.message.reply_photo(
        photo=cand.photo_file_id,
        caption=caption,
        reply_markup=match_keyboard()
    )
    return MATCH

async def match_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    uid = update.effective_user.id
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]

    if choice == "❤️ Me gusta":
        # notify profile owner
        await context.bot.send_message(
            chat_id=cand.id,
            text="🎉 ¡Tu perfil recibió un like!"
        )
        # register like and check mutual
        mutual = db.record_like(uid, cand.id)
        if mutual:
            await update.message.reply_text(
                f"🎉 ¡Match mutuo con @{cand.fullname}! Podéis hablar por privado.",
                reply_markup=main_keyboard()
            )
            await context.bot.send_message(
                chat_id=cand.id,
                text=f"🎉 ¡Match mutuo con @{update.effective_user.full_name}! Podéis hablar."
            )
        # continue to next
        context.user_data['idx'] += 1
        return await show_next_profile(update, context)

    if choice == "🚫 No me gusta":
        context.user_data['idx'] += 1
        return await show_next_profile(update, context)

    if choice == "🛑 Dejar Emparejar":
        await update.message.reply_text("Emparejar detenido.", reply_markup=main_keyboard())
        return ConversationHandler.END

    # fallback
    await update.message.reply_text("Volviendo al menú principal.", reply_markup=main_keyboard())
    return ConversationHandler.END

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Operación cancelada.", reply_markup=main_keyboard())
    return ConversationHandler.END

# Application setup
if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Profile conversation
    perfil_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📄 Perfil$"), handle_message)],
        states={
            PROFILE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_menu)],
            PHOTO:        [MessageHandler(filters.PHOTO, perfil_photo)],
            DESC:         [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_description)],
            INSTA:        [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_instagram)],
            GENDER:       [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_gender)],
            COUNTRY:      [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_country)],
            CITY:         [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_city)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    app.add_handler(perfil_conv)

    # Match conversation
    match_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^👥 Emparejar$"), match_start)],
        states={ MATCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, match_choice)] },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    app.add_handler(match_conv)

    # General fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot iniciado con flujos de perfil y emparejar")
    app.run_polling(drop_pending_updates=True)
