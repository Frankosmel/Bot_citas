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

# Estados del ConversationHandler
(
    MENU,
    PROFILE_MENU,
    PHOTO, DESC, INSTA, GENDER, PREF_GENDER, COUNTRY, CITY,
    SEARCH,
) = range(10)

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== Teclados =====

def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["👤 Mi Perfil", "🔍 Buscar gente cerca"],
        ["🔔 Promociones",   "🛑 Salir"]
    ], resize_keyboard=True)

def profile_menu_keyboard(has_profile: bool) -> ReplyKeyboardMarkup:
    kb = []
    if not has_profile:
        kb.append(["🆕 Crear mi perfil"])
    else:
        kb.append(["👁️ Ver mi perfil"])
        kb.append(["✏️ Editar mis datos"])
        kb.append(["❌ Borrar mi perfil"])
    kb.append(["🔙 Menú principal"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def search_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Me interesa",   callback_data="search_like"),
        InlineKeyboardButton("🚫 No es para mí", callback_data="search_dislike"),
    ]])

def notify_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Me interesa",   callback_data="notify_like"),
        InlineKeyboardButton("🚫 No es para mí", callback_data="notify_dislike"),
    ]])

def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["🔙 Menú principal"]], resize_keyboard=True)

def contact_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📩 Contactar", url=f"tg://user?id={user_id}")
    ]])

# ===== Handlers =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start — Bienvenida detallada y ayuda."""
    db = context.bot_data["db"]
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    await update.message.reply_text(
        "🎉 ¡Bienvenido a LeoMatch! 🎉\n\n"
        "Este bot te permite:\n"
        "1️⃣ Crear y gestionar tu perfil con foto, descripción, género, ubicación e Instagram.\n"
        "2️⃣ Buscar perfiles de usuarios cercanos según tu ciudad y preferencias de género.\n"
        "3️⃣ Dar ❤️ “Me interesa” o 🚫 “No es para mí” en cada perfil.\n"
        "4️⃣ Si ambos se dan ❤️ mutuamente, recibirán un botón para contactar directamente.\n\n"
        "🔹 Usa ‘Mi Perfil’ para crear/ver/editar o borrar tu perfil.\n"
        "🔹 Usa ‘Buscar gente cerca’ para iniciar la búsqueda de posibles coincidencias.\n"
        "🔹 Pulsa /help para ver esta guía en cualquier momento.\n\n"
        "Selecciona una opción:",
        reply_markup=main_keyboard()
    )
    return MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help — Mostrar guía breve."""
    await update.message.reply_text(
        "🔹 Usa los botones bajo teclado para navegar:\n"
        "   • 👤 Mi Perfil: gestiona tu perfil.\n"
        "   • 🔍 Buscar gente cerca: explora y da like/dislike.\n"
        "🔹 En búsqueda, usa botones inline para indicar interés.\n"
        "🔹 Si hay match mutuo, recibirás un botón de contacto.\n"
        "🔹 Envía /cancelar para volver al menú principal en cualquier momento."
    )

async def menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejo de opciones del menú principal."""
    text = update.message.text
    uid = update.effective_user.id
    db = context.bot_data["db"]

    if text == "👤 Mi Perfil":
        has = db.has_profile(uid)
        await update.message.reply_text("⚙️ Menú de Perfil:", reply_markup=profile_menu_keyboard(has))
        return PROFILE_MENU

    if text == "🔍 Buscar gente cerca":
        return await search_start(update, context)

    if text == "🔔 Promociones":
        prem = db.is_premium(uid)
        msg = "Para recibir promociones hazte Premium 💎" if not prem else "No hay promociones nuevas."
        await update.message.reply_text(msg, reply_markup=main_keyboard())
        return MENU

    if text == "🛑 Salir":
        db.unregister_user(uid)
        await update.message.reply_text("👋 Te has dado de baja. Usa /start para volver.", reply_markup=main_keyboard())
        return ConversationHandler.END

    await update.message.reply_text("❌ Opción no válida. Usa los botones del menú.", reply_markup=main_keyboard())
    return MENU

# ----- Gestión de perfil -----

async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejo del submenú Perfil."""
    text = update.message.text
    uid = update.effective_user.id
    db = context.bot_data["db"]

    # Crear o editar perfil
    if text in ("🆕 Crear mi perfil", "✏️ Editar mis datos"):
        await update.message.reply_text("📸 Por favor, envía tu foto de perfil.")
        return PHOTO

    # Ver perfil
    if text == "👁️ Ver mi perfil":
        p = db.get_profile(uid)
        if not p or not p.photo_file_id:
            await update.message.reply_text(
                "❌ No tienes perfil. Usa Crear/Editar para configurarlo.",
                reply_markup=profile_menu_keyboard(False)
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
                    f"🔗 IG: @{p.instagram or '—'}\n\n"
                    f"📝 {p.description}"
                ),
                reply_markup=profile_menu_keyboard(True)
            )
        return PROFILE_MENU

    # Borrar perfil
    if text == "❌ Borrar mi perfil":
        await update.message.reply_text("⚠️ Confirma borrado enviando Sí o No.")
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
        return MENU

    await update.message.reply_text("❌ Opción inválida en Perfil.", reply_markup=profile_menu_keyboard(True))
    return PROFILE_MENU

# ----- Crear / Editar perfil -----

async def perfil_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la foto y solicita descripción."""
    if not update.message.photo:
        await update.message.reply_text("❗ Debes enviar una foto.")
        return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("📝 Ahora, envía una breve descripción (una frase).")
    return DESC

async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la descripción y solicita Instagram."""
    context.user_data['description'] = update.message.text
    await update.message.reply_text("🔗 Comparte tu usuario de Instagram (sin @), o envía — si no tienes.")
    return INSTA

async def perfil_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe Instagram y solicita género."""
    context.user_data['instagram'] = update.message.text.strip() or ""
    await update.message.reply_text("⚧️ Indica tu género (por ejemplo: Hombre, Mujer u Otro).")
    return GENDER

async def perfil_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe género y solicita preferencia."""
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("🔎 ¿Qué género te interesa conocer? (Hombre, Mujer u Otro).")
    return PREF_GENDER

async def perfil_pref_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe preferencia de género y solicita país."""
    context.user_data['pref_gender'] = update.message.text
    await update.message.reply_text("🌎 Por favor, envía tu país de residencia.")
    return COUNTRY

async def perfil_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe país y solicita ciudad."""
    context.user_data['country'] = update.message.text
    await update.message.reply_text("🏙️ Finalmente, ¿en qué ciudad vives?")
    return CITY

async def perfil_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe ciudad, guarda el perfil completo y regresa."""
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
        reply_markup=main_keyboard()
    )
    context.user_data.clear()
    return MENU

# ----- Búsqueda de perfiles -----

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia búsqueda cargando candidatos."""
    uid = update.effective_user.id
    db = context.bot_data["db"]
    context.user_data['candidates'] = db.get_potential_matches(uid)
    context.user_data['idx'] = 0
    if not context.user_data['candidates']:
        await update.message.reply_text("🚫 No hay perfiles cerca de ti.", reply_markup=main_keyboard())
        return MENU
    return await show_next(update, context)

async def show_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra siguiente perfil con botones inline de interés."""
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
        reply_markup=search_inline_keyboard()
    )
    return SEARCH

async def search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja Me interesa / No es para mí y guarda last_searcher."""
    q = update.callback_query
    await q.answer()
    db = context.bot_data["db"]
    uid = q.from_user.id
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]

    # Guardamos quién inició el like para notificar más tarde
    context.user_data['last_searcher'] = uid

    if q.data == "search_like":
        # Enviar notificación a A con botones inline de confirmación
        me = db.get_profile(uid)
        await context.bot.send_photo(
            chat_id=cand.id,
            photo=me.photo_file_id,
            caption=(
                f"👤 {me.fullname}\n"
                f"🌎 País: {me.country}\n"
                f"🏙️ Ciudad: {me.city}\n\n"
                f"📝 {me.description}"
            ),
            reply_markup=notify_inline_keyboard()
        )

    # Avanzar al siguiente perfil
    context.user_data['idx'] += 1
    if context.user_data['idx'] >= len(context.user_data['candidates']):
        # Editar última foto indicando fin
        await q.edit_message_caption(
            caption=q.message.caption + "\n\n🚫 Se acabaron los perfiles.",
            reply_markup=None
        )
        # Botón de volver
        await context.bot.send_message(
            chat_id=uid,
            text="🔙 Pulsa Menú principal para regresar.",
            reply_markup=back_keyboard()
        )
        return MENU

    # Borrar mensaje anterior y mostrar siguiente
    await q.delete_message()
    return await show_next(update, context)

# ----- Callback de notificación de match -----

async def notify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa la confirmación de A y notifica a ambos."""
    q = update.callback_query
    await q.answer()
    db = context.bot_data["db"]
    A_id = q.from_user.id
    B_id = context.user_data.get('last_searcher')
    if not B_id:
        return

    if q.data == "notify_like":
        # Editar notificación de A
        await q.edit_message_caption(
            caption=q.message.caption + "\n\n🎉 ¡Match mutuo!",
            reply_markup=contact_inline_keyboard(B_id)
        )
        # Notificar a B
        other = db.get_profile(A_id)
        await context.bot.send_photo(
            chat_id=B_id,
            photo=other.photo_file_id,
            caption=(
                f"🎉 ¡Match mutuo con @{other.id}!\n"
                f"👤 {other.fullname}\n"
                f"🌎 País: {other.country}\n"
                f"🏙️ Ciudad: {other.city}\n\n"
                f"📝 {other.description}"
            ),
            reply_markup=contact_inline_keyboard(A_id)
        )
    else:
        # Rechazo de A
        await q.edit_message_text("❌ Notificación cerrada.", reply_markup=None)

# ----- Cancelar -----

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Operación cancelada.", reply_markup=main_keyboard())
    return ConversationHandler.END

# ===== Configuración y arranque =====

def main():
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.bot_data["db"] = Database(config.DB_URL)

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU:          [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_choice)],
            PROFILE_MENU:  [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_menu)],
            PHOTO:         [MessageHandler(filters.PHOTO, perfil_photo)],
            DESC:          [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_description)],
            INSTA:         [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_instagram)],
            GENDER:        [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_gender)],
            PREF_GENDER:   [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_pref_gender)],
            COUNTRY:       [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_country)],
            CITY:          [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_city)],
            SEARCH:        [CallbackQueryHandler(search_callback, pattern="^search_")],
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
