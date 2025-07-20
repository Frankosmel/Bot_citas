#!/usr/bin/env python3
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

# Estados de conversación
(
    PROFILE_MENU,
    PHOTO, DESC, INSTA, GENDER, PREF_GENDER, COUNTRY, CITY,
    SEARCH
) = range(9)

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Teclados
def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("👤 Mi Perfil"), KeyboardButton("🔍 Buscar gente cerca")],
        [KeyboardButton("🔔 Promociones"),   KeyboardButton("🛑 Salir")]
    ], resize_keyboard=True)

def profile_menu_keyboard(has_profile: bool) -> ReplyKeyboardMarkup:
    kb = []
    if not has_profile:
        kb.append([KeyboardButton("🆕 Crear mi perfil")])
    else:
        kb.append([KeyboardButton("👁️ Ver mi perfil")])
        kb.append([KeyboardButton("✏️ Editar mis datos")])
        kb.append([KeyboardButton("❌ Borrar mi perfil")])
    kb.append([KeyboardButton("🔙 Menú principal")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def search_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("❤️ Me interesa"), KeyboardButton("🚫 No es para mí")],
        [KeyboardButton("🔙 Finalizar búsqueda")]
    ], resize_keyboard=True)

def notify_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Me gusta",     callback_data="notify_like"),
        InlineKeyboardButton("🚫 No me gusta",   callback_data="notify_dislike"),
    ]])

def contact_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    # boton para contactar por user ID
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📩 Contactar", url=f"tg://user?id={user_id}")
    ]])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data["db"]
    u = update.effective_user
    db.register_user(u.id, u.full_name)
    await update.message.reply_text(
        "🎉 ¡Bienvenido a LeoMatch! 🎉\n"
        "Conecta con gente cercana:\n\n"
        "👤 Mi Perfil — gestiona tu información\n"
        "🔍 Buscar gente cerca — encuentra matches\n\n"
        "Elige una opción:",
        reply_markup=main_keyboard()
    )
    return PROFILE_MENU

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usa los botones bajo teclado para navegar.\n"
        "Envía /cancelar en cualquier momento para volver al menú."
    )

# Handler de mensajes generales
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    db = context.bot_data["db"]

    if text == "👤 Mi Perfil":
        has = db.has_profile(uid)
        await update.message.reply_text(
            "⚙️ Menú de Perfil:",
            reply_markup=profile_menu_keyboard(has)
        )
        return PROFILE_MENU

    if text == "🔍 Buscar gente cerca":
        return await search_start(update, context)

    if text == "🔔 Promociones":
        prem = db.is_premium(uid)
        msg = "Para recibir promociones 📢 hazte Premium 💎" if not prem else "No hay promociones nuevas."
        await update.message.reply_text(msg, reply_markup=main_keyboard())
        return PROFILE_MENU

    if text == "🛑 Salir":
        db.unregister_user(uid)
        await update.message.reply_text("👋 Has salido. Usa /start para regresar.", reply_markup=main_keyboard())
        return ConversationHandler.END

    await update.message.reply_text("❌ Opción no válida. Usa los botones.", reply_markup=main_keyboard())
    return PROFILE_MENU

# --- Flujo de Perfil ---
async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    db = context.bot_data["db"]

    if text == "🆕 Crear mi perfil" or text == "✏️ Editar mis datos":
        await update.message.reply_text("📸 Por favor, envíame la foto que quieras usar como perfil.")
        return PHOTO

    if text == "👁️ Ver mi perfil":
        p = db.get_profile(uid)
        if not p or not p.photo_file_id:
            await update.message.reply_text(
                "❌ No tienes perfil aún. Pulsa ✏️ Editar mis datos para crearlo.",
                reply_markup=profile_menu_keyboard(False)
            )
        else:
            await update.message.reply_photo(
                photo=p.photo_file_id,
                caption=(
                    f"👤 Nombre: {p.fullname}\n"
                    f"🌎 País: {p.country}\n"
                    f"🏙️ Ciudad: {p.city}\n"
                    f"⚧️ Género: {p.gender}\n"
                    f"🔎 Busco: {p.pref_gender}\n"
                    f"🔗 Instagram: @{p.instagram or '—'}\n\n"
                    f"📝 \"{p.description}\""
                ),
                reply_markup=profile_menu_keyboard(True)
            )
        return PROFILE_MENU

    if text == "❌ Borrar mi perfil":
        await update.message.reply_text(
            "⚠️ ¿Estás seguro de borrar tu perfil? Envía “Sí” para confirmar o “No” para cancelar."
        )
        context.user_data["deleting"] = True
        return PROFILE_MENU

    if text and context.user_data.get("deleting"):
        if text.lower() in ("sí", "si"):
            db.delete_profile(uid)
            await update.message.reply_text("🗑️ Tu perfil ha sido eliminado.", reply_markup=main_keyboard())
            context.user_data.clear()
            return PROFILE_MENU
        else:
            await update.message.reply_text("✅ Cancelado. Aquí está tu perfil:", reply_markup=profile_menu_keyboard(True))
            context.user_data.clear()
            return PROFILE_MENU

    if text == "🔙 Menú principal":
        await update.message.reply_text("🔙 Volviendo al menú principal.", reply_markup=main_keyboard())
        return PROFILE_MENU

    await update.message.reply_text("❌ Opción inválida en Perfil.", reply_markup=profile_menu_keyboard(True))
    return PROFILE_MENU

# Guardar campos de perfil
async def perfil_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❗️Debes enviar una foto.")
        return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("📝 Ahora, envía una breve descripción de ti (una frase).")
    return DESC

async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("🔗 Comparte tu usuario de Instagram (sin @), o envía “—” si no tienes.")
    return INSTA

async def perfil_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['instagram'] = update.message.text.strip() or ""
    await update.message.reply_text("⚧️ Indica tu género (por ejemplo: Hombre, Mujer u Otro).")
    return GENDER

async def perfil_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("🔎 ¿Qué género te interesa conocer? (Masculino, Femenino u Otro).")
    return PREF_GENDER

async def perfil_pref_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pref_gender'] = update.message.text
    await update.message.reply_text("🌎 Por favor, indica tu país de residencia.")
    return COUNTRY

async def perfil_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['country'] = update.message.text
    await update.message.reply_text("🏙️ Finalmente, ¿en qué ciudad vives?")
    return CITY

async def perfil_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = context.user_data
    db = context.bot_data["db"]
    db.save_profile(
        uid,
        photo_file_id = u['photo'],
        description   = u['description'],
        instagram     = u['instagram'],
        gender        = u['gender'],
        pref_gender   = u['pref_gender'],
        country       = u['country'],
        city          = update.message.text
    )
    await update.message.reply_text(
        "✅ Tu perfil se ha guardado con éxito.\n"
        "👁️ Usa 'Ver mi perfil' para revisarlo.",
        reply_markup=main_keyboard()
    )
    context.user_data.clear()
    return PROFILE_MENU

# --- Flujo de búsqueda de perfiles ---
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = context.bot_data["db"]
    context.user_data['candidates'] = db.get_potential_matches(uid)
    context.user_data['idx'] = 0
    if not context.user_data['candidates']:
        await update.message.reply_text("🚫 No hay perfiles cerca de ti.", reply_markup=main_keyboard())
        return PROFILE_MENU
    return await show_next(update, context)

async def show_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]
    # guardamos notifier para notificación
    context.user_data['notifier'] = {
        "id":   update.effective_user.id,
        "name": update.effective_user.full_name,
        "photo": update.effective_user.user_data.get('photo'),
        "country": context.bot_data["db"].get_profile(update.effective_user.id).country,
        "city": context.bot_data["db"].get_profile(update.effective_user.id).city,
        "description": context.bot_data["db"].get_profile(update.effective_user.id).description,
    }
    await update.message.reply_photo(
        photo=cand.photo_file_id,
        caption=(
            f"👤 {cand.fullname}\n"
            f"🌎 {cand.country}\n"
            f"🏙️ {cand.city}\n\n"
            f"📝 {cand.description}"
        ),
        reply_markup=search_keyboard()
    )
    return SEARCH

async def search_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]
    db = context.bot_data["db"]

    if text == "❤️ Me interesa":
        db.record_like(uid, cand.id)
        # notificar a A (cand) con tu perfil
        notifier = context.user_data['notifier']
        await context.bot.send_photo(
            chat_id=cand.id,
            photo=notifier['photo'],
            caption=(
                f"👤 {notifier['name']}\n"
                f"🌎 {notifier['country']}\n"
                f"🏙️ {notifier['city']}\n\n"
                f"📝 {notifier['description']}"
            ),
            reply_markup=notify_inline_keyboard()
        )
        # avanzar
        context.user_data['idx'] += 1
        if context.user_data['idx'] >= len(context.user_data['candidates']):
            await update.message.reply_text("🚫 No hay más perfiles disponibles.", reply_markup=main_keyboard())
            return PROFILE_MENU
        return await show_next(update, context)

    if text == "🚫 No es para mí":
        context.user_data['idx'] += 1
        if context.user_data['idx'] >= len(context.user_data['candidates']):
            await update.message.reply_text("🚫 No hay más perfiles disponibles.", reply_markup=main_keyboard())
            return PROFILE_MENU
        return await show_next(update, context)

    if text == "🔙 Finalizar búsqueda":
        await update.message.reply_text("🔙 Búsqueda terminada.", reply_markup=main_keyboard())
        return PROFILE_MENU

    await update.message.reply_text("❌ Opción no válida.", reply_markup=search_keyboard())
    return SEARCH

# --- Callback de notificación de like ---
async def notify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    db = context.bot_data["db"]
    # quien notificó (B)
    notifier = context.user_data.get('notifier')
    # A es quien recibe notificación (q.from_user)
    A_id = q.from_user.id
    if data == "notify_like":
        # es mutuo: le notificamos a ambos
        # edit mensaje de A
        await q.edit_message_caption(
            caption=q.message.caption + "\n\n🎉 ¡Match mutuo!",
            reply_markup=contact_inline_keyboard(notifier['id'])
        )
        # enviar a B
        await context.bot.send_message(
            chat_id=notifier['id'],
            text=(
                f"🎉 ¡Match mutuo con @{q.from_user.username}!\n"
                "Pulsa el botón para contactar."
            ),
            reply_markup=contact_inline_keyboard(A_id)
        )
    else:
        # no gusta: cerrar
        await q.edit_message_text("❌ Notificación cerrada.", reply_markup=None)

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Operación cancelada.", reply_markup=main_keyboard())
    return ConversationHandler.END

# Configuración del bot
def main():
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.bot_data["db"] = Database(config.DB_URL)

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PROFILE_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            ],
            PHOTO: [MessageHandler(filters.PHOTO, perfil_photo)],
            DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_description)],
            INSTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_instagram)],
            GENDER:[MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_gender)],
            PREF_GENDER:[MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_pref_gender)],
            COUNTRY:[MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_country)],
            CITY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_city)],
            SEARCH:[MessageHandler(filters.TEXT & ~filters.COMMAND, search_choice)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(notify_callback, pattern="^notify_"))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("🤖 Bot iniciado")
    app.run_polling()

if __name__ == "__main__":
    main()

