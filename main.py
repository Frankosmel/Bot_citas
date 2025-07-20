# main.py

import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
MATCH_NOTIFY = 1

# Inline keyboards
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Buscar Perfiles", callback_data="start_search"),
         InlineKeyboardButton("📄 Perfil",         callback_data="profile_menu")],
        [InlineKeyboardButton("🔔 Promos",         callback_data="promos"),
         InlineKeyboardButton("🛑 Salir",          callback_data="logout")],
    ])

def profile_menu_keyboard(has_profile: bool):
    buttons = []
    if not has_profile:
        buttons.append([InlineKeyboardButton("🆕 Crear Perfil", callback_data="create_profile")])
    else:
        buttons.append([InlineKeyboardButton("✏️ Editar Perfil", callback_data="edit_profile")])
        buttons.append([InlineKeyboardButton("🗑️ Eliminar Perfil", callback_data="delete_profile")])
    buttons.append([InlineKeyboardButton("🏠 Menú", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(buttons)

def search_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Me gusta", callback_data="like"),
        InlineKeyboardButton("🚯 No me gusta", callback_data="dislike"),
        InlineKeyboardButton("✋ Salir",      callback_data="stop_search"),
    ]])

def notify_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Me gusta", callback_data="notify_like"),
        InlineKeyboardButton("🚯 No me gusta", callback_data="notify_dislike"),
        InlineKeyboardButton("✋ Salir",          callback_data="stop_notify"),
    ]])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    await update.message.reply_text(
        "Leo: ¡Ligar. Citas y amigos! 💕\n"
        "Contacto 👉 @frankosmel\n\n"
        f"¡Hola, {user.first_name}! Elige una opción:",
        reply_markup=main_keyboard()
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa los botones, o /cancelar para salir de un flujo.")

# Main menu callbacks
async def menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id

    if data == "start_search":
        # iniciar búsqueda
        context.user_data['candidates'] = db.get_potential_matches(uid)
        context.user_data['idx'] = 0
        return await show_profile(q, context, SEARCH)

    if data == "promos":
        text = "Para promos hazte Premium 💎" if not db.is_premium(uid) else "No hay promos."
        await q.edit_message_text(text, reply_markup=main_keyboard())
        return

    if data == "profile_menu":
        has = db.has_profile(uid)
        await q.edit_message_text("Gestión de Perfil:", reply_markup=profile_menu_keyboard(has))
        return PROFILE_MENU

    if data == "logout":
        db.unregister_user(uid)
        await q.edit_message_text("Has salido. /start para volver.", reply_markup=main_keyboard())
        return

    # perfil submenú
    if data in ("create_profile", "edit_profile"):
        await q.edit_message_text("📷 Envía tu foto de perfil:")
        return PHOTO

    if data == "delete_profile":
        db.delete_profile(uid)
        await q.edit_message_text("✅ Perfil eliminado.", reply_markup=main_keyboard())
        return ConversationHandler.END

    if data == "back_to_menu":
        await q.edit_message_text("Menú principal:", reply_markup=main_keyboard())
        return ConversationHandler.END

# Mostrar perfil candidato o notificación
async def show_profile(query, context, state):
    uid = query.from_user.id
    idx = context.user_data['idx']
    lst = context.user_data['candidates']
    if idx >= len(lst):
        await query.edit_message_text("No quedan perfiles.", reply_markup=main_keyboard())
        return ConversationHandler.END

    cand = lst[idx]
    caption = (
        f"👤 {cand.fullname}\n"
        f"📍 {cand.country}, {cand.city}\n\n"
        f"{cand.description}"
    )
    kb = search_keyboard() if state == SEARCH else notify_keyboard()
    # edit media
    await query.edit_message_media(
        media=InputMediaPhoto(media=cand.photo_file_id, caption=caption),
        reply_markup=kb
    )
    return state

# Callbacks para búsqueda
async def search_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    choice = q.data
    uid = q.from_user.id

    if choice == "stop_search":
        await q.edit_message_caption("Búsqueda detenida.", reply_markup=main_keyboard())
        return ConversationHandler.END

    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]

    if choice == "like":
        # notificar al dueño
        context.user_data['notify_target'] = cand
        # prepara lista de notificaciones
        context.user_data['notify_queue'] = [cand]
        return await notify_cb(update, context)

    # dislike sigue
    context.user_data['idx'] += 1
    return await show_profile(q, context, SEARCH)

# Callbacks para notificación de like
async def notify_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    choice = q.data
    uid = q.from_user.id
    cand = context.user_data['notify_target']

    # Muestra al dueño del perfil quien le dio like
    caption = (
        f"👤 {update.effective_user.full_name}\n"
        f"📍 {update.effective_user.location if hasattr(update.effective_user, 'location') else ''}\n\n"
        f"{context.user_data.get('description','') or ''}"
    )
    kb = search_keyboard()  # mismos botones para recusar o aceptar match

    if choice == "notify_like":
        # registrar y comprobar mutuo
        mutual = db.record_like(uid, cand.id)
        if mutual:
            # match: enviar contacto a ambos
            text_you = f"🎉 ¡Match mutuo! Contacta: @{cand.fullname}"
            text_them = f"🎉 ¡Match mutuo! Contacta: @{update.effective_user.full_name}"
            await q.edit_message_caption(text_you, reply_markup=main_keyboard())
            await context.bot.send_message(chat_id=cand.id, text=text_them)
            return ConversationHandler.END
        # no es mutuo: mostramos perfil tuyo al dueño
        await q.edit_message_media(
            media=InputMediaPhoto(media=update.effective_message.photo[-1].file_id, caption=caption),
            reply_markup=kb
        )
        return MATCH_NOTIFY

    if choice == "notify_dislike" or choice == "stop_notify":
        await q.edit_message_text("Notificación completada.", reply_markup=main_keyboard())
        return ConversationHandler.END

# Flujo creación de perfil
async def perfil_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Envía una foto, por favor.")
        return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("📝 Envía descripción:")
    return DESC

async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("📸 Usuario de Instagram (sin @):")
    return INSTA

async def perfil_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['instagram'] = update.message.text
    await update.message.reply_text("👤 Género:")
    return GENDER

async def perfil_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("🌍 País:")
    return COUNTRY

async def perfil_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['country'] = update.message.text
    await update.message.reply_text("🏙️ Ciudad:")
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
    await update.message.reply_text("✅ Perfil guardado.", reply_markup=main_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# Cancelar
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Operación cancelada.", reply_markup=main_keyboard())
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # menú principal
    app.add_handler(CallbackQueryHandler(menu_cb, pattern="^(start_search|promos|profile_menu|logout|create_profile|edit_profile|delete_profile|back_to_menu)$"))

    # búsqueda
    app.add_handler(CallbackQueryHandler(search_cb, pattern="^(like|dislike|stop_search)$"))

    # notificación
    app.add_handler(CallbackQueryHandler(notify_cb, pattern="^(notify_like|notify_dislike|stop_notify)$"))

    # perfil
    profile_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_cb, pattern="^(create_profile|edit_profile)$")],
        states={
            PHOTO:   [MessageHandler(filters.PHOTO, perfil_photo)],
            DESC:    [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_description)],
            INSTA:   [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_instagram)],
            GENDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_gender)],
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_country)],
            CITY:    [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_city)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    app.add_handler(profile_conv)

    # fallback de texto
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_command))

    logger.info("🤖 Bot iniciado con inline search y notificaciones")
    app.run_polling(drop_pending_updates=True)
