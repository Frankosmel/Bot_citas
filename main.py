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

# Estados
PROFILE_MENU, PHOTO, DESC, INSTA, GENDER, PREF_GENDER, COUNTRY, CITY, SEARCH = range(9)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Teclados
def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("👤 Mi Perfil"), KeyboardButton("🔍 Buscar gente cerca")],
        [KeyboardButton("🔔 Promociones"),   KeyboardButton("🛑 Salir")]
    ], resize_keyboard=True)

def profile_menu_keyboard(has_profile: bool):
    kb = []
    if not has_profile:
        kb.append([KeyboardButton("🆕 Crear mi perfil")])
    else:
        kb.append([KeyboardButton("👁️ Ver mi perfil")])
        kb.append([KeyboardButton("✏️ Editar mis datos")])
        kb.append([KeyboardButton("❌ Borrar mi perfil")])
    kb.append([KeyboardButton("🔙 Menú principal")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def search_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("❤️ Me interesa"), KeyboardButton("🚫 No es para mí")],
        [KeyboardButton("🔙 Finalizar búsqueda")]
    ], resize_keyboard=True)

def notify_inline():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Corresponder", callback_data="notify_like"),
        InlineKeyboardButton("🚫 Rechazar",    callback_data="notify_dislike"),
    ]])

def contact_inline(user_id: int):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📩 Contactar", url=f"tg://user?id={user_id}")
    ]])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data["db"]
    u = update.effective_user
    db.register_user(u.id, u.full_name)
    await update.message.reply_text(
        "🎉 ¡Bienvenido a LeoMatch! 🎉\n\n"
        "👤 Mi Perfil — gestiona tu información\n"
        "🔍 Buscar gente cerca — encuentra posibles matches\n\n"
        "Elige una opción:",
        reply_markup=main_keyboard()
    )
    return PROFILE_MENU

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usa los botones bajo teclado para moverte.\n"
        "Envía /cancelar para volver al menú."
    )

# Manejo general de texto
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
        msg = "Para recibir promociones hazte Premium 💎" if not prem else "No hay promociones nuevas."
        await update.message.reply_text(msg, reply_markup=main_keyboard())
        return PROFILE_MENU

    if text == "🛑 Salir":
        db.unregister_user(uid)
        await update.message.reply_text("👋 Has salido. /start para volver.", reply_markup=main_keyboard())
        return ConversationHandler.END

    await update.message.reply_text("❌ Opción no válida. Usa los botones.", reply_markup=main_keyboard())
    return PROFILE_MENU

# --- Perfil ---
async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    db = context.bot_data["db"]

    # Crear / editar
    if text in ("🆕 Crear mi perfil", "✏️ Editar mis datos"):
        await update.message.reply_text("📸 Envía la foto que quieras usar como perfil.")
        return PHOTO

    # Ver perfil
    if text == "👁️ Ver mi perfil":
        p = db.get_profile(uid)
        if not p or not p.photo_file_id:
            await update.message.reply_text(
                "❌ No tienes perfil. Pulsa ✏️ Editar mis datos para crearlo.",
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
                    f"📝 {p.description}"
                ),
                reply_markup=profile_menu_keyboard(True)
            )
        return PROFILE_MENU

    # Borrar perfil
    if text == "❌ Borrar mi perfil":
        await update.message.reply_text(
            "⚠️ Confirma borrado de perfil: envía “Sí” para proceder o “No” para cancelar."
        )
        context.user_data["confirm_delete"] = True
        return PROFILE_MENU

    if context.user_data.get("confirm_delete"):
        if text.lower() in ("sí", "si"):
            db.delete_profile(uid)
            await update.message.reply_text("🗑️ Perfil eliminado.", reply_markup=main_keyboard())
        else:
            await update.message.reply_text("✅ Eliminación cancelada.", reply_markup=profile_menu_keyboard(True))
        context.user_data.pop("confirm_delete", None)
        return PROFILE_MENU

    # Volver
    if text == "🔙 Menú principal":
        await update.message.reply_text("🔙 Volviendo al menú principal.", reply_markup=main_keyboard())
        return PROFILE_MENU

    await update.message.reply_text("❌ Opción inválida en Perfil.", reply_markup=profile_menu_keyboard(True))
    return PROFILE_MENU

# Flujo de creación/edición
async def perfil_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❗ Envía una foto válida.")
        return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("📝 Ahora, envía una breve descripción (una frase).")
    return DESC

async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("🔗 Tu usuario de Instagram (sin @) o “—” si no tienes.")
    return INSTA

async def perfil_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['instagram'] = update.message.text.strip() or ""
    await update.message.reply_text("⚧️ Indica tu género (Hombre, Mujer u Otro).")
    return GENDER

async def perfil_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("🔎 ¿Qué género te interesa conocer?")
    return PREF_GENDER

async def perfil_pref_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pref_gender'] = update.message.text
    await update.message.reply_text("🌎 Por favor, envía tu país de residencia.")
    return COUNTRY

async def perfil_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['country'] = update.message.text
    await update.message.reply_text("🏙️ Finalmente, indica tu ciudad.")
    return CITY

async def perfil_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = context.user_data
    db = context.bot_data["db"]
    db.save_profile(
        uid,
        photo_file_id=u['photo'],
        description=u['description'],
        instagram=u['instagram'],
        gender=u['gender'],
        pref_gender=u['pref_gender'],
        country=u['country'],
        city=update.message.text
    )
    await update.message.reply_text(
        "✅ Perfil guardado con éxito.\n"
        "👁️ Usa ‘Ver mi perfil’ para revisarlo.",
        reply_markup=main_keyboard()
    )
    context.user_data.clear()
    return PROFILE_MENU

# --- Búsqueda de perfiles ---
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
    # Guardar datos de quien busca para notificar
    me = context.user_data['searcher'] = {
        "id": update.effective_user.id,
        "photo": context.user_data.get('photo'),
        "fullname": update.effective_user.full_name,
        "country": context.bot_data["db"].get_profile(update.effective_user.id).country,
        "city": context.bot_data["db"].get_profile(update.effective_user.id).city,
        "description": context.bot_data["db"].get_profile(update.effective_user.id).description
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
        # Notificar a A (cand) con datos de B
        B = context.user_data['searcher']
        await context.bot.send_photo(
            chat_id=cand.id,
            photo=B['photo'],
            caption=(
                f"👤 {B['fullname']}\n"
                f"🌎 {B['country']}\n"
                f"🏙️ {B['city']}\n\n"
                f"📝 {B['description']}"
            ),
            reply_markup=notify_inline()
        )
        # Avanzar
        context.user_data['idx'] += 1

    elif text == "🚫 No es para mí":
        context.user_data['idx'] += 1

    elif text == "🔙 Finalizar búsqueda":
        await update.message.reply_text("🔙 Búsqueda finalizada.", reply_markup=main_keyboard())
        return PROFILE_MENU

    # Mostrar siguiente o fin
    if context.user_data['idx'] >= len(context.user_data['candidates']):
        await update.message.reply_text("🚫 No hay más perfiles disponibles.", reply_markup=main_keyboard())
        return PROFILE_MENU
    return await show_next(update, context)

# --- Callbacks de notificación ---
async def notify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    B = context.user_data.get('searcher')
    A_id = q.from_user.id

    if data == "notify_like":
        # Match mutuo: editar mensaje de A
        await q.edit_message_caption(
            caption=q.message.caption + "\n\n🎉 ¡Match mutuo!",
            reply_markup=contact_inline(B['id'])
        )
        # Notificar a B
        await context.bot.send_message(
            chat_id=B['id'],
            text=f"🎉 ¡Match mutuo con @{q.from_user.username}! Pulsa Contactar.",
            reply_markup=contact_inline(A_id)
        )
    else:
        # Rechazo: cerrar
        await q.edit_message_text("❌ Notificación cerrada.", reply_markup=None)

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Operación cancelada.", reply_markup=main_keyboard())
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.bot_data["db"] = Database(config.DB_URL)

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PROFILE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            PHOTO:        [MessageHandler(filters.PHOTO, perfil_photo)],
            DESC:         [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_description)],
            INSTA:        [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_instagram)],
            GENDER:       [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_gender)],
            PREF_GENDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_pref_gender)],
            COUNTRY:      [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_country)],
            CITY:         [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_city)],
            SEARCH:       [MessageHandler(filters.TEXT & ~filters.COMMAND, search_choice)],
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
