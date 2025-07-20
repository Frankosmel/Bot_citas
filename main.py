#!/usr/bin/env python3
import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup,
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
(
    MENU,
    PROFILE_MENU,
    PHOTO, DESC, INSTA, GENDER, PREF_GENDER, COUNTRY, CITY,
    SEARCH,
) = range(10)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Teclados
def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["👤 Mi Perfil", "🔍 Buscar gente cerca"],
        ["🔔 Promociones", "🛑 Salir"]
    ], resize_keyboard=True)

def profile_kb(has_profile: bool) -> ReplyKeyboardMarkup:
    kb = []
    if not has_profile:
        kb.append(["🆕 Crear mi perfil"])
    else:
        kb += [["👁️ Ver mi perfil"], ["✏️ Editar mis datos"], ["❌ Borrar mi perfil"]]
    kb.append(["🔙 Menú principal"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def search_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Me interesa",   callback_data="search_like"),
        InlineKeyboardButton("🚫 No es para mí", callback_data="search_dislike"),
    ]])

def notify_inline_kb(liker_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Me interesa",   callback_data=f"notify_like:{liker_id}"),
        InlineKeyboardButton("🚫 No es para mí", callback_data=f"notify_dislike:{liker_id}"),
    ]])

def back_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["🔙 Menú principal"]], resize_keyboard=True)

def contact_inline(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📩 Contactar", url=f"tg://user?id={user_id}")
    ]])

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start — Bienvenida detallada."""
    db = context.bot_data["db"]
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    await update.message.reply_text(
        "🎉 ¡Bienvenid@ al bot *Citas y Amigos*! 🎉\n\n"
        "Este bot te permite:\n"
        "1️⃣ Crear y gestionar tu perfil con foto, descripción, género y ubicación.\n"
        "2️⃣ Buscar perfiles de usuarios cercanos según tu ciudad y preferencias.\n"
        "3️⃣ Dar ❤️ “Me interesa” o 🚫 “No es para mí” en cada perfil.\n"
        "4️⃣ Si ambos se dan ❤️ mutuamente, recibirán un botón para contactar.\n\n"
        "🔹 Usa ‘Mi Perfil’ para crear/ver/editar o borrar tu perfil.\n"
        "🔹 Usa ‘Buscar gente cerca’ para explorar perfiles.\n"
        "🔹 Pulsa /help para ver esta guía en cualquier momento.\n\n"
        "Selecciona una opción:",
        reply_markup=main_kb(),
        parse_mode="Markdown"
    )
    return MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help — Mostrar guía breve."""
    await update.message.reply_text(
        "🔹 Usa los botones del teclado o inline según se indique.\n"
        "🔹 En cualquier flujo, envía /cancelar para volver al menú principal."
    )

async def menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejo de opciones del menú principal."""
    text = update.message.text
    uid = update.effective_user.id
    db = context.bot_data["db"]

    if text == "👤 Mi Perfil":
        await update.message.reply_text(
            "⚙️ Menú de Perfil:",
            reply_markup=profile_kb(db.has_profile(uid))
        )
        return PROFILE_MENU

    if text == "🔍 Buscar gente cerca":
        return await search_start(update, context)

    if text == "🔔 Promociones":
        msg = "Para recibir promociones 📢 hazte Premium 💎" if not db.is_premium(uid) else "✅ No hay promociones nuevas."
        await update.message.reply_text(msg, reply_markup=main_kb())
        return MENU

    if text == "🛑 Salir":
        db.unregister_user(uid)
        await update.message.reply_text(
            "👋 Te has dado de baja. Usa /start para regresar.",
            reply_markup=main_kb()
        )
        return ConversationHandler.END

    await update.message.reply_text("❌ Opción no válida. Usa los botones del menú.", reply_markup=main_kb())
    return MENU

# Gestión de perfil
async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    db = context.bot_data["db"]

    if text in ("🆕 Crear mi perfil", "✏️ Editar mis datos"):
        await update.message.reply_text("📸 Por favor, envía tu foto de perfil.")
        return PHOTO

    if text == "👁️ Ver mi perfil":
        p = db.get_profile(uid)
        if not p or not p.photo_file_id:
            await update.message.reply_text(
                "❌ No tienes perfil. Usa Crear/Editar para configurarlo.",
                reply_markup=profile_kb(False)
            )
        else:
            await update.message.reply_photo(
                photo=p.photo_file_id,
                caption=(
                    f"👤 {p.fullname}\n"
                    f"🌎 País: {p.country}\n"
                    f"🏙️ Ciudad: {p.city}\n"
                    f"⚧️ Género: {p.gender}\n"
                    f"🔎 Busca: {p.pref_gender}\n"
                    f"🔗 Instagram: @{p.instagram or '—'}\n\n"
                    f"📝 {p.description}"
                ),
                reply_markup=profile_kb(True)
            )
        return PROFILE_MENU

    if text == "❌ Borrar mi perfil":
        await update.message.reply_text("⚠️ Confirma borrado enviando Sí o No.")
        context.user_data["confirm_delete"] = True
        return PROFILE_MENU

    if context.user_data.get("confirm_delete"):
        if text.lower() in ("sí", "si"):
            db.delete_profile(uid)
            await update.message.reply_text("🗑️ Perfil eliminado.", reply_markup=main_kb())
        else:
            await update.message.reply_text("✅ Eliminación cancelada.", reply_markup=profile_kb(True))
        context.user_data.pop("confirm_delete", None)
        return PROFILE_MENU

    if text == "🔙 Menú principal":
        await update.message.reply_text("🔙 Volviendo al menú principal.", reply_markup=main_kb())
        return MENU

    await update.message.reply_text("❌ Opción inválida en Perfil.", reply_markup=profile_kb(db.has_profile(uid)))
    return PROFILE_MENU

# Crear / Editar perfil
async def perfil_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❗ Debes enviar una foto.")
        return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("📝 Ahora, envía una breve descripción (una frase).")
    return DESC

async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("🔗 Comparte tu usuario de Instagram (sin @), o envía — si no tienes.")
    return INSTA

async def perfil_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['instagram'] = update.message.text.strip() or ""
    await update.message.reply_text("⚧️ Indica tu género (por ejemplo: Hombre, Mujer u Otro).")
    return GENDER

async def perfil_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("🔎 ¿Qué género te interesa conocer? (Hombre, Mujer u Otro).")
    return PREF_GENDER

async def perfil_pref_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pref_gender'] = update.message.text
    await update.message.reply_text("🌎 Por favor, envía tu país de residencia.")
    return COUNTRY

async def perfil_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['country'] = update.message.text
    await update.message.reply_text("🏙️ Finalmente, ¿en qué ciudad vives?")
    return CITY

async def perfil_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = context.user_data
    db = context.bot_data["db"]
    db.save_profile(
        uid,
        photo_file_id=data['photo'],
        description=data['description'],
        instagram=data['instagram'],
        gender=data['gender'],
        pref_gender=data['pref_gender'],
        country=data['country'],
        city=update.message.text
    )
    await update.message.reply_text(
        "✅ Tu perfil ha sido guardado correctamente.\n"
        "👁️ Usa 'Ver mi perfil' para revisarlo.",
        reply_markup=main_kb()
    )
    context.user_data.clear()
    return MENU

# Búsqueda de perfiles
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = context.bot_data["db"]
    context.user_data['candidates'] = db.get_potential_matches(uid)
    context.user_data['idx'] = 0
    if not context.user_data['candidates']:
        await update.message.reply_text("🚫 No hay perfiles cerca de ti.", reply_markup=main_kb())
        return MENU
    return await show_next(update, context)

async def show_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]
    await update.message.reply_photo(
        photo=cand.photo_file_id,
        caption=(
            f"👤 {cand.fullname}\n"
            f"🌎 País: {cand.country}\n"
            f"🏙️ Ciudad: {cand.city}\n\n"
            f"📝 {cand.description}"
        ),
        reply_markup=search_inline_kb()
    )
    return SEARCH

async def search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    db = context.bot_data["db"]
    uid = q.from_user.id
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]

    if q.data == "search_like":
        me = db.get_profile(uid)
        # Notificación a Y: "A X le ha gustado tu perfil"
        await context.bot.send_photo(
            chat_id=cand.id,
            photo=me.photo_file_id,
            caption=(
                f"🎉 ¡A *{me.fullname}* le ha gustado tu perfil!\n\n"
                f"👤 Nombre: {me.fullname}\n"
                f"🌎 País: {me.country}\n"
                f"🏙️ Ciudad: {me.city}\n\n"
                f"📝 {me.description}"
            ),
            reply_markup=notify_inline_kb(uid),
            parse_mode="Markdown"
        )

    context.user_data['idx'] += 1
    if context.user_data['idx'] >= len(context.user_data['candidates']):
        await q.edit_message_caption(
            caption=q.message.caption + "\n\n🚫 Se acabaron los perfiles.",
            reply_markup=None
        )
        await context.bot.send_message(
            chat_id=uid,
            text="🔙 Pulsa Menú principal para regresar.",
            reply_markup=back_kb()
        )
        return MENU

    await q.delete_message()
    return await show_next(update, context)

async def notify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    db = context.bot_data["db"]
    data, liker_id = q.data.split(":")
    liker_id = int(liker_id)
    receiver_id = q.from_user.id

    if data == "notify_like":
        await q.edit_message_caption(
            caption=q.message.caption + "\n\n🎉 ¡Match mutuo!",
            reply_markup=contact_inline(liker_id)
        )
        other = db.get_profile(receiver_id)
        await context.bot.send_photo(
            chat_id=liker_id,
            photo=other.photo_file_id,
            caption=(
                f"🎉 ¡Match mutuo con @{other.id}!\n"
                f"👤 {other.fullname}\n"
                f"🌎 País: {other.country}\n"
                f"🏙️ Ciudad: {other.city}\n\n"
                f"📝 {other.description}"
            ),
            reply_markup=contact_inline(receiver_id)
        )
    else:
        await q.edit_message_text("❌ Notificación cerrada.", reply_markup=None)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Operación cancelada.", reply_markup=main_kb())
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.bot_data["db"] = Database(config.DB_URL)

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU:         [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_choice)],
            PROFILE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_menu)],
            PHOTO:        [MessageHandler(filters.PHOTO, perfil_photo)],
            DESC:         [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_description)],
            INSTA:        [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_instagram)],
            GENDER:       [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_gender)],
            PREF_GENDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_pref_gender)],
            COUNTRY:      [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_country)],
            CITY:         [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_city)],
            SEARCH:       [CallbackQueryHandler(search_callback, pattern="^search_")],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(notify_callback, pattern="^notify_"))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("🤖 Bot iniciado correctamente")
    app.run_polling()

if __name__ == "__main__":
    main()
