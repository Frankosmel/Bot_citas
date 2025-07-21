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

def main_keyboard(db: Database, uid: int) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton("👤 Mi Perfil"), KeyboardButton("🔍 Buscar gente cerca")],
        [KeyboardButton("🏆 Top usuarios"), KeyboardButton("💰 Mi saldo")],
        [KeyboardButton("🔔 Promociones"), KeyboardButton("🛑 Salir")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

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

def search_inline_keyboard(uid: int, super_likes: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton("❤️ Me interesa", callback_data="search_like"),
        InlineKeyboardButton("🚫 No es para mí", callback_data="search_dislike"),
    ]
    if super_likes > 0:
        buttons.append(InlineKeyboardButton("💥 Super Like", callback_data="search_super"))
    return InlineKeyboardMarkup([buttons])

def notify_inline_keyboard(liker_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Me interesa", callback_data=f"notify_like:{liker_id}"),
        InlineKeyboardButton("🚫 No es para mí", callback_data=f"notify_dislike:{liker_id}"),
    ]])

def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton("🔙 Menú principal")]], resize_keyboard=True)

def contact_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📩 Contactar", url=f"tg://user?id={user_id}")
    ]])

# ===== Handlers =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data["db"]
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    await update.message.reply_text(
        "🎉 ¡Bienvenid@ al bot *Citas y Amigos*! 🎉\n\n"
        "1️⃣ Crea y gestiona tu perfil con foto, descripción, género y ubicación.\n"
        "2️⃣ Busca gente cerca y da ❤️ “Me interesa” o 🚫 “No es para mí”.\n"
        "3️⃣ Si hay match mutuo, recibirás un botón para contactar.\n"
        "4️⃣ Usa 💥 Super Like (crédito) para contactar directo sin esperar confirmación.\n"
        "5️⃣ Consulta 🏆 Top usuarios y 💰 Mi saldo para ver tus ganancias.\n\n"
        "Selecciona una opción:",
        reply_markup=main_keyboard(db, user.id),
        parse_mode="Markdown"
    )
    return MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔹 Usa los botones bajo teclado o inline según se indique.\n"
        "🔹 🏆 Top usuarios muestra el ranking actual.\n"
        "🔹 💰 Mi saldo muestra tus ganancias (50 CUP/Super Like recibido).\n"
        "🔹 /cancelar para volver al menú principal."
    )

async def menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    db = context.bot_data["db"]

    if text == "👤 Mi Perfil":
        await update.message.reply_text(
            "⚙️ Menú de Perfil:",
            reply_markup=profile_menu_keyboard(db.has_profile(uid))
        )
        return PROFILE_MENU

    if text == "🔍 Buscar gente cerca":
        return await search_start(update, context)

    if text == "🏆 Top usuarios":
        top = db.get_top_users(5)
        msg = "🏆 *Top 5 Usuarios*\n\n"
        for i, u in enumerate(top, start=1):
            msg += (
                f"{i}. {u.fullname}\n"
                f"   ❤️ Likes recibidos: {u.likes_received}\n"
                f"   💥 SL recibidos: {u.super_likes_received}\n\n"
            )
        await update.message.reply_text(msg, parse_mode="Markdown",
                                        reply_markup=main_keyboard(db, uid))
        return MENU

    if text == "💰 Mi saldo":
        me = db.get_user(uid)
        saldo = (me.super_likes_received or 0) * 50
        await update.message.reply_text(
            f"💰 *Tu saldo acumulado:* {saldo} CUP\n\n"
            "Cada Super Like recibido genera 50 CUP.\n"
            "Para retirar, ponte en contacto con el administrador.",
            parse_mode="Markdown",
            reply_markup=main_keyboard(db, uid)
        )
        return MENU

    if text == "🔔 Promociones":
        promo_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🥇 1 SL — 360 CUP", callback_data="buy_1")],
            [InlineKeyboardButton("🥈 5 SL — 1800 CUP", callback_data="buy_5")],
            [InlineKeyboardButton("🥉 10 SL — 3600 CUP", callback_data="buy_10")],
        ])
        await update.message.reply_text(
            "🎁 Paquetes de Super Likes:\n(1 SL = 360 CUP = 1 USD)",
            reply_markup=promo_kb
        )
        return MENU

    if text == "🛑 Salir":
        db.unregister_user(uid)
        await update.message.reply_text(
            "👋 Te has dado de baja. Envía /start para volver.",
            reply_markup=main_keyboard(db, uid)
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "❌ Opción inválida.",
        reply_markup=main_keyboard(db, uid)
    )
    return MENU

# ----- Gestión de perfil -----

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
                reply_markup=profile_menu_keyboard(False)
            )
        else:
            await update.message.reply_photo(
                photo=p.photo_file_id,
                caption=(
                    f"👤 *{p.fullname}*\n"
                    f"🌎 País: {p.country}\n"
                    f"🏙️ Ciudad: {p.city}\n"
                    f"⚧️ Género: {p.gender}\n"
                    f"🔎 Busca: {p.pref_gender}\n"
                    f"🔗 Instagram: @{p.instagram or '—'}\n\n"
                    f"📝 {p.description}"
                ),
                reply_markup=profile_menu_keyboard(True),
                parse_mode="Markdown"
            )
        return PROFILE_MENU

    if text == "❌ Borrar mi perfil":
        await update.message.reply_text("⚠️ Confirma borrado enviando Sí o No.")
        context.user_data["confirm_delete"] = True
        return PROFILE_MENU

    if context.user_data.get("confirm_delete"):
        if text.lower() in ("sí", "si"):
            db.delete_profile(uid)
            await update.message.reply_text(
                "🗑️ Tu perfil ha sido eliminado.",
                reply_markup=main_keyboard(db, uid)
            )
        else:
            await update.message.reply_text(
                "✅ Eliminación cancelada.",
                reply_markup=profile_menu_keyboard(True)
            )
        context.user_data.pop("confirm_delete", None)
        return PROFILE_MENU

    if text == "🔙 Menú principal":
        await update.message.reply_text(
            "🔙 Volviendo al menú principal.",
            reply_markup=main_keyboard(db, uid)
        )
        return MENU

    await update.message.reply_text(
        "❌ Opción inválida en Perfil.",
        reply_markup=profile_menu_keyboard(db.has_profile(uid))
    )
    return PROFILE_MENU

# Crear / Editar perfil

async def perfil_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❗ Debes enviar una foto.")
        return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("📝 Ahora, envía una breve descripción de ti.")
    return DESC

async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text(
        "🔗 Comparte tu usuario de Instagram (sin @), o envía — si no lo tienes."
    )
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
        "👁️ Usa ‘Ver mi perfil’ para revisarlo.",
        reply_markup=main_keyboard(db, uid)
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
        await update.message.reply_text(
            "🚫 No hay perfiles cerca.",
            reply_markup=main_keyboard(db, uid)
        )
        return MENU
    return await show_next(update, context)

async def show_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['idx']
    cand = context.user_data['candidates'][idx]
    uid = update.effective_user.id
    db = context.bot_data["db"]
    sl_credits = db.get_user(uid).super_likes or 0

    await update.message.reply_photo(
        photo=cand.photo_file_id,
        caption=(
            f"👤 *{cand.fullname}*\n"
            f"🌎 País: {cand.country}\n"
            f"🏙️ Ciudad: {cand.city}\n\n"
            f"📝 {cand.description}"
        ),
        reply_markup=search_inline_keyboard(uid, sl_credits),
        parse_mode="Markdown"
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
        db.record_like(uid, cand.id)
        await context.bot.send_photo(
            chat_id=cand.id,
            photo=me.photo_file_id,
            caption=(
                f"🎉 ¡A *{me.fullname}* le ha gustado tu perfil!\n\n"
                f"👤 {me.fullname}\n"
                f"🌎 País: {me.country}\n"
                f"🏙️ Ciudad: {me.city}\n\n"
                f"📝 {me.description}"
            ),
            reply_markup=notify_inline_keyboard(uid),
            parse_mode="Markdown"
        )

    elif q.data == "search_super":
        if db.use_super_like(uid):
            me = db.get_profile(uid)
            db.record_super_like(uid, cand.id)
            await context.bot.send_photo(
                chat_id=cand.id,
                photo=me.photo_file_id,
                caption=(
                    f"💥 *Super Like* de *{me.fullname}* 🎉\n\n"
                    f"👤 {me.fullname}\n"
                    f"🌎 País: {me.country}\n"
                    f"🏙️ Ciudad: {me.city}\n\n"
                    f"📝 {me.description}\n\n"
                    "¡No hace falta confirmación, aquí tienes el contacto!"
                ),
                reply_markup=contact_inline_keyboard(uid),
                parse_mode="Markdown"
            )
            await context.bot.send_message(
                chat_id=uid,
                text="✅ Has usado 1 Super Like. Se ha establecido el contacto.",
                reply_markup=main_keyboard(db, uid)
            )
        else:
            await context.bot.send_message(
                chat_id=uid,
                text="❌ No tienes Super Likes. Ve a Promociones para comprar.",
                reply_markup=main_keyboard(db, uid)
            )

    context.user_data['idx'] += 1
    if context.user_data['idx'] >= len(context.user_data['candidates']):
        await q.edit_message_caption(
            caption=q.message.caption + "\n\n🚫 Se acabaron los perfiles.",
            reply_markup=None
        )
        await context.bot.send_message(
            chat_id=uid,
            text="🔙 Pulsa ‘Menú principal’ para volver.",
            reply_markup=back_keyboard()
        )
        return MENU

    await q.delete_message()
    return await show_next(update, context)

# Confirmación de match mutuo

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
            reply_markup=contact_inline_keyboard(liker_id)
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
            reply_markup=contact_inline_keyboard(receiver_id)
        )
    else:
        await q.edit_message_text("❌ Notificación cerrada.", reply_markup=None)

# Comprar Super Likes

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    db = context.bot_data["db"]

    if q.data == "buy_1":
        db.purchase_super_likes(uid, 1)
        text = "✅ Has comprado 1 Super Like."
    elif q.data == "buy_5":
        db.purchase_super_likes(uid, 5)
        text = "✅ Has comprado 5 Super Likes."
    else:
        db.purchase_super_likes(uid, 10)
        text = "✅ Has comprado 10 Super Likes."

    credits = db.get_user(uid).super_likes or 0
    await q.edit_message_text(f"{text}\n🎉 Ahora tienes {credits} SL.", reply_markup=None)

# Grant Super (admin)

async def grant_super(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in config.ADMINS:
        return await update.message.reply_text("❌ No estás autorizado.")
    args = context.args
    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit():
        return await update.message.reply_text("Uso: /grant_super <user_id> <cantidad>")
    target, cnt = int(args[0]), int(args[1])
    db = context.bot_data["db"]
    db.purchase_super_likes(target, cnt)
    await update.message.reply_text(f"✅ Otorgados {cnt} SL a {target}.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = context.bot_data["db"]
    await update.message.reply_text(
        "👋 Operación cancelada.",
        reply_markup=main_keyboard(db, uid)
    )
    return ConversationHandler.END

# ===== Configuración y arranque =====

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
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_"))
    app.add_handler(CommandHandler("grant_super", grant_super))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("🤖 Bot iniciado correctamente")
    app.run_polling()

if __name__ == "__main__":
    main()
