# main.py

import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
SEARCH = 0

# Reply keyboards
def main_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton("🔍 Buscar Perfiles"), KeyboardButton("🔔 Promociones")],
        [KeyboardButton("📄 Perfil"),           KeyboardButton("🛑 Salir")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def profile_menu_keyboard(has_profile: bool) -> ReplyKeyboardMarkup:
    buttons = []
    if not has_profile:
        buttons.append([KeyboardButton("🆕 Crear Perfil")])
    else:
        buttons.extend([
            [KeyboardButton("📋 Ver Mi Perfil")],
            [KeyboardButton("✏️ Editar Perfil")],
            [KeyboardButton("🗑️ Eliminar Perfil")],
        ])
    buttons.append([KeyboardButton("🏠 Volver")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def search_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("❤️ Me gusta"), KeyboardButton("🚯 No me gusta")],
        [KeyboardButton("✋ Salir Búsqueda")]
    ], resize_keyboard=True)

# Inline keyboard for notification
def notify_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❤️ Corresponder", callback_data="notify_correspond"),
            InlineKeyboardButton("🚯 Rechazar",     callback_data="notify_reject"),
            InlineKeyboardButton("✋ Salir",         callback_data="notify_exit"),
        ]
    ])

def contact_inline_keyboard(username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Contactar", url=f"https://t.me/{username}")]
    ])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    count = len(db.get_all_user_ids())
    await update.message.reply_text(
        "🎉 ¡Bienvenido a LeoMatch! 🎉\n"
        "Conecta con gente nueva.\n\n"
        f"📊 Usuarios registrados: {count}\n\n"
        f"Hola, {user.first_name}! Elige una opción:",
        reply_markup=main_keyboard()
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usa los botones bajo teclado para navegar.\n"
        "Envía /cancelar para salir de cualquier flujo."
    )

# Fallback to main menu
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if text == "🔍 Buscar Perfiles":
        return await search_start(update, context)

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
            "🖊️ Gestión de Perfil:",
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

# Profile submenu handler
async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if text in ("🆕 Crear Perfil", "✏️ Editar Perfil"):
        await update.message.reply_text("📷 Por favor, envía tu foto de perfil:")
        return PHOTO

    if text == "📋 Ver Mi Perfil":
        p = db.get_profile(uid)
        if not p or not p.photo_file_id:
            await update.message.reply_text("No tienes perfil. Crea uno primero.", reply_markup=main_keyboard())
        else:
            await update.message.reply_photo(
                photo=p.photo_file_id,
                caption=(
                    f"👤 {p.fullname}\n"
                    f"📍 {p.country}, {p.city}\n"
                    f"📸 instagram.com/{p.instagram}\n\n"
                    f"{p.description}"
                ),
                reply_markup=main_keyboard()
            )
        return ConversationHandler.END

    if text == "🗑️ Eliminar Perfil":
        db.delete_profile(uid)
        await update.message.reply_text("✅ Perfil eliminado.", reply_markup=main_keyboard())
        return ConversationHandler.END

    if text == "🏠 Volver":
        await update.message.reply_text("Menú principal:", reply_markup=main_keyboard())
        return ConversationHandler.END

    await update.message.reply_text("Opción inválida en Perfil.", reply_markup=main_keyboard())
    return ConversationHandler.END

# Profile creation/edit flow
async def perfil_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Envía una foto, por favor.")
        return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
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
        photo_file_id=context.user_data['photo'],
        description=context.user_data['description'],
        instagram=context.user_data['instagram'],
        gender=context.user_data['gender'],
        country=context.user_data['country'],
        city=update.message.text
    )
    await update.message.reply_text("✅ Perfil guardado correctamente.", reply_markup=main_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# Search/match flow
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    context.user_data['candidates'] = db.get_potential_matches(uid)
    context.user_data['idx'] = 0
    if not context.user_data['candidates']:
        await update.message.reply_text("No hay perfiles cercanos.", reply_markup=main_keyboard())
        return ConversationHandler.END
    return await show_next(update, context)

async def show_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]
    await update.message.reply_photo(
        photo=cand.photo_file_id,
        caption=(
            f"👤 {cand.fullname}\n"
            f"📍 {cand.country}, {cand.city}\n\n"
            f"{cand.description}"
        ),
        reply_markup=search_keyboard()
    )
    return SEARCH

async def search_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]

    if text == "❤️ Me gusta":
        db.record_like(uid, cand.id)
        # notify owner
        await context.bot.send_photo(
            chat_id=cand.id,
            photo=cand.photo_file_id,
            caption=(
                f"👤 {cand.fullname}\n"
                f"📍 {cand.country}, {cand.city}\n\n"
                f"{cand.description}"
            ),
            reply_markup=notify_inline_keyboard()
        )
        # advance to next in search
        context.user_data['idx'] += 1
        return await show_next(update, context)

    if text == "🚯 No me gusta":
        context.user_data['idx'] += 1
        return await show_next(update, context)

    if text == "✋ Salir Búsqueda":
        await update.message.reply_text("Búsqueda detenida.", reply_markup=main_keyboard())
        return ConversationHandler.END

    return ConversationHandler.END

# Notification callbacks
async def notify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id
    # The candidate who liked this user was the previous 'cand' in context.job?
    # We'll retrieve it from the last sent photo's caption metadata:
    # Instead, store the liker in context.user_data on search_choice:
    # as context.user_data['last_notifier']
    notifier = context.user_data.get('last_notifier')
    if not notifier:
        return await q.edit_message_text("Error interno.", reply_markup=main_keyboard())

    if data == "notify_correspond":
        # Replace with contact button
        await q.edit_message_caption(
            caption=q.message.caption,
            reply_markup=contact_inline_keyboard(notifier.username)
        )
    else:
        # reject or exit
        await q.edit_message_text("Notificación cerrada.", reply_markup=main_keyboard())

# Cancel flow
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Operación cancelada.", reply_markup=main_keyboard())
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # Handlers
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

    # Search conversation
    search_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔍 Buscar Perfiles$"), search_start)],
        states={SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_choice)]},
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    app.add_handler(search_conv)

    # Notification inline callbacks
    app.add_handler(CallbackQueryHandler(notify_callback, pattern="^notify_"))

    # General fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot iniciado correctamente")
    app.run_polling(drop_pending_updates=True)
