# main.py

import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
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

# States
PROFILE_MENU, PHOTO, DESC, INSTA, GENDER, PREF_GENDER, COUNTRY, CITY = range(8)
SEARCH = 0

# Keyboards
def main_keyboard():
    users = len(db.get_all_user_ids())
    return ReplyKeyboardMarkup([
        [f"📊 Usuarios: {users}"],
        ["🔍 Buscar Perfiles", "🔔 Promociones"],
        ["📄 Perfil",           "🛑 Salir"],
    ], resize_keyboard=True)

def profile_menu_keyboard(has_profile):
    kb = []
    if not has_profile:
        kb.append(["🆕 Crear Perfil"])
    else:
        kb += [
            ["📋 Ver Mi Perfil"],
            ["✏️ Editar Perfil"],
            ["🗑️ Eliminar Perfil"],
        ]
    kb.append(["🏠 Volver"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def search_keyboard():
    return ReplyKeyboardMarkup([
        ["❤️ Me gusta", "🚯 No me gusta"],
        ["✋ Salir Búsqueda"]
    ], resize_keyboard=True)

def notify_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ Me gusta", callback_data="notify_like"),
         InlineKeyboardButton("🚯 No me gusta", callback_data="notify_dislike")]
    ])

def contact_inline(username):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📩 Contactar", url=f"https://t.me/{username}")
    ]])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.register_user(u.id, u.full_name)
    await update.message.reply_text(
        "🎉 ¡Bienvenido a LeoMatch! 🎉\nConecta con gente cercana a ti.\n\n"
        f"📊 Usuarios registrados: {len(db.get_all_user_ids())}\n"
        f"Hola, {u.first_name}! Elige:",
        reply_markup=main_keyboard()
    )

# /help
async def help_command(update, context):
    await update.message.reply_text("Usa botones para navegar. /cancelar para volver.")

# Main fallback
async def handle_message(update, context):
    t = update.message.text
    uid = update.effective_user.id

    if t == "🔍 Buscar Perfiles":
        return await search_start(update, context)

    if t == "🔔 Promociones":
        prem = db.is_premium(uid)
        await update.message.reply_text(
            "Hazte Premium 💎" if not prem else "No hay promos.",
            reply_markup=main_keyboard()
        )
        return

    if t == "📄 Perfil":
        has = db.has_profile(uid)
        await update.message.reply_text("Perfil:", reply_markup=profile_menu_keyboard(has))
        return PROFILE_MENU

    if t == "🛑 Salir":
        db.unregister_user(uid)
        await update.message.reply_text("Salida ok. /start para vuelta.", reply_markup=main_keyboard())
        return

    await update.message.reply_text("Elige opción.", reply_markup=main_keyboard())

# Profile submenu
async def profile_menu(update, context):
    t = update.message.text
    uid = update.effective_user.id

    if t in ("🆕 Crear Perfil", "✏️ Editar Perfil"):
        await update.message.reply_text("📷 Envía foto:")
        return PHOTO

    if t == "📋 Ver Mi Perfil":
        p = db.get_profile(uid)
        if not p or not p.photo_file_id:
            await update.message.reply_text("Sin perfil.", reply_markup=main_keyboard())
        else:
            await update.message.reply_photo(
                p.photo_file_id,
                caption=(
                    f"👤 {p.fullname}\n"
                    f"📍 {p.country}, {p.city}\n"
                    f"📸 insta.com/{p.instagram}\n\n"
                    f"{p.description}"
                ),
                reply_markup=main_keyboard()
            )
        return ConversationHandler.END

    if t == "🗑️ Eliminar Perfil":
        db.delete_profile(uid)
        await update.message.reply_text("Perfil borrado.", reply_markup=main_keyboard())
        return ConversationHandler.END

    if t == "🏠 Volver":
        await update.message.reply_text("Menú:", reply_markup=main_keyboard())
        return ConversationHandler.END

    await update.message.reply_text("Opción invalida.", reply_markup=main_keyboard())
    return ConversationHandler.END

# Profile flow
async def perfil_photo(update, context):
    if not update.message.photo:
        await update.message.reply_text("Foto pls.")
        return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("📝 Descripción:")
    return DESC

async def perfil_description(update, context):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("📸 Instagram (sin @):")
    return INSTA

async def perfil_instagram(update, context):
    context.user_data['instagram'] = update.message.text
    await update.message.reply_text("👤 Tu género:")
    return GENDER

async def perfil_gender(update, context):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("👀 ¿Qué género buscas?")
    return PREF_GENDER

async def perfil_pref_gender(update, context):
    context.user_data['pref_gender'] = update.message.text
    await update.message.reply_text("🌍 País:")
    return COUNTRY

async def perfil_country(update, context):
    context.user_data['country'] = update.message.text
    await update.message.reply_text("🏙️ Ciudad:")
    return CITY

async def perfil_city(update, context):
    uid = update.effective_user.id
    u = context.user_data
    db.save_profile(
        uid,
        u['photo'], u['description'], u['instagram'],
        u['gender'], u['pref_gender'],
        u['country'], u['city'] if 'city' in u else update.message.text
    )
    await update.message.reply_text("Perfil guardado ✅", reply_markup=main_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# Search flow
async def search_start(update, context):
    uid = update.effective_user.id
    context.user_data['candidates'] = db.get_potential_matches(uid)
    context.user_data['idx'] = 0
    if not context.user_data['candidates']:
        await update.message.reply_text("No hay perfiles.", reply_markup=main_keyboard())
        return ConversationHandler.END
    return await show_next(update, context)

async def show_next(update, context):
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]
    await update.message.reply_photo(
        cand.photo_file_id,
        caption=(
            f"👤 {cand.fullname}\n"
            f"📍 {cand.country}, {cand.city}\n\n"
            f"{cand.description}"
        ),
        reply_markup=search_keyboard()
    )
    return SEARCH

async def search_choice(update, context):
    t = update.message.text
    uid = update.effective_user.id
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]

    if t == "❤️ Me gusta":
        db.record_like(uid, cand.id)
        # notificamos a A con TU perfil y botones
        u = update.effective_user
        await context.bot.send_photo(
            chat_id=cand.id,
            photo=u.user_data['photo'],
            caption=(
                f"👤 {u.full_name}\n"
                f"📍 {u.location if hasattr(u,'location') else ''}\n\n"
                f"{u.user_data['description']}"
            ),
            reply_markup=notify_inline()
        )
        # guardamos A para el callback
        context.user_data['notifier'] = u

    if t in ("❤️ Me gusta", "🚯 No me gusta"):
        context.user_data['idx'] += 1
        if context.user_data['idx'] >= len(context.user_data['candidates']):
            await update.message.reply_text("No hay más perfiles.", reply_markup=main_keyboard())
            return ConversationHandler.END
        return await show_next(update, context)

    if t == "✋ Salir Búsqueda":
        await update.message.reply_text("Búsqueda detenida.", reply_markup=main_keyboard())
        return ConversationHandler.END

    return ConversationHandler.END

# Notification callback
async def notify_callback(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data
    notifier = context.user_data.get('notifier')
    if not notifier:
        return
    if data == "notify_like":
        # match mutuo: ambos reciben botón contactar
        u = update.effective_user
        await q.edit_message_caption(
            caption=q.message.caption + f"\n\n🎉 ¡Match mutuo! @{u.username}",
            reply_markup=contact_inline(notifier.username)
        )
        await context.bot.send_photo(
            chat_id=notifier.id,
            photo=q.message.photo.file_id,
            caption=q.message.caption + f"\n\n🎉 ¡Match mutuo! @{u.username}",
            reply_markup=contact_inline(u.username)
        )
    else:
        # reject
        await q.edit_message_text("Notificación cerrada.", reply_markup=main_keyboard())

# Cancel
async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text("Cancelado.", reply_markup=main_keyboard())
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    perfil_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📄 Perfil$"), handle_message)],
        states={
            PROFILE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_menu)],
            PHOTO:        [MessageHandler(filters.PHOTO, perfil_photo)],
            DESC:         [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_description)],
            INSTA:        [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_instagram)],
            GENDER:       [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_gender)],
            PREF_GENDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_pref_gender)],
            COUNTRY:      [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_country)],
            CITY:         [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_city)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    app.add_handler(perfil_conv)

    search_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔍 Buscar Perfiles$"), search_start)],
        states={SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_choice)]},
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    app.add_handler(search_conv)

    app.add_handler(CallbackQueryHandler(notify_callback, pattern="^notify_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot iniciado con preferencias y match mutuo")
    app.run_polling(drop_pending_updates=True)
