# main.py
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
    SEARCH, SUPER
) = range(11)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# — Teclados —

def main_kb(db: Database, uid: int) -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton("👤 Mi Perfil"), KeyboardButton("🔍 Buscar gente cerca")]]
    credits = db.get_user(uid).super_likes or 0
    if credits > 0:
        buttons.append([KeyboardButton(f"💥 Super Like ({credits})")])
    buttons.append([KeyboardButton("🔔 Promociones"), KeyboardButton("🛑 Salir")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def profile_kb(has_profile: bool) -> ReplyKeyboardMarkup:
    kb = []
    if not has_profile:
        kb.append([KeyboardButton("🆕 Crear mi perfil")])
    else:
        kb += [
            [KeyboardButton("👁️ Ver mi perfil")],
            [KeyboardButton("✏️ Editar mis datos")],
            [KeyboardButton("❌ Borrar mi perfil")]
        ]
    kb.append([KeyboardButton("🔙 Menú principal")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def search_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Me interesa", callback_data="search_like"),
        InlineKeyboardButton("🚫 No es para mí", callback_data="search_dislike"),
    ]])

def notify_inline_kb(liker_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❤️ Me interesa", callback_data=f"notify_like:{liker_id}"),
        InlineKeyboardButton("🚫 No es para mí", callback_data=f"notify_dislike:{liker_id}"),
    ]])

def back_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton("🔙 Menú principal")]], resize_keyboard=True)

def contact_inline(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📩 Contactar", url=f"tg://user?id={user_id}")
    ]])

# — Handlers —

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data["db"]
    u = update.effective_user
    db.register_user(u.id, u.full_name)
    await update.message.reply_text(
        "🎉 ¡Bienvenid@ al bot *Citas y Amigos*! 🎉\n\n"
        "1️⃣ Crea y gestiona tu perfil con foto, descripción, género y ubicación.\n"
        "2️⃣ Busca usuarios cercanos y da ❤️ “Me interesa” o 🚫 “No es para mí”.\n"
        "3️⃣ Si es mutuo, recibirás un botón para contactar.\n"
        "4️⃣ Usa 💥 Super Like (crédito) para contactar directo.\n\n"
        "Selecciona una opción:",
        reply_markup=main_kb(db, u.id),
        parse_mode="Markdown"
    )
    return MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔹 Usa botones bajo teclado o inline según se indique.\n"
        "🔹 Envía /cancelar para volver al menú principal."
    )

async def menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    db = context.bot_data["db"]

    if text == "👤 Mi Perfil":
        await update.message.reply_text("⚙️ Menú de Perfil:", reply_markup=profile_kb(db.has_profile(uid)))
        return PROFILE_MENU

    if text == "🔍 Buscar gente cerca":
        return await search_start(update, context)

    if text.startswith("💥 Super Like"):
        return await super_start(update, context)

    if text == "🔔 Promociones":
        promo_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🥇 1 Super Like — 360 CUP", callback_data="buy_1")],
            [InlineKeyboardButton("🥈 5 Super Likes — 1800 CUP", callback_data="buy_5")],
            [InlineKeyboardButton("🥉 10 Super Likes — 3600 CUP", callback_data="buy_10")],
        ])
        await update.message.reply_text(
            "🎁 Paquetes de Super Likes:\n(1 SL = 360 CUP ≈ $1 USD)",
            reply_markup=promo_kb
        )
        return MENU

    if text == "🛑 Salir":
        db.unregister_user(uid)
        await update.message.reply_text("👋 Te has dado de baja.", reply_markup=main_kb(db, uid))
        return ConversationHandler.END

    await update.message.reply_text("❌ Opción inválida.", reply_markup=main_kb(db, uid))
    return MENU

# — Grant Super (admin) —
async def grant_super(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in config.ADMINS:
        return await update.message.reply_text("❌ No estás autorizado.")
    args = context.args
    if len(args)!=2 or not args[0].isdigit() or not args[1].isdigit():
        return await update.message.reply_text("Uso: /grant_super <user_id> <cantidad>")
    target, cnt = int(args[0]), int(args[1])
    db = context.bot_data["db"]
    db.purchase_super_likes(target, cnt)
    await update.message.reply_text(f"✅ Otorgados {cnt} SL a {target}.")

# — Perfil Handlers —

async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text; uid = update.effective_user.id
    db = context.bot_data["db"]
    if text in ("🆕 Crear mi perfil","✏️ Editar mis datos"):
        await update.message.reply_text("📸 Envía tu foto de perfil.")
        return PHOTO
    if text=="👁️ Ver mi perfil":
        p = db.get_profile(uid)
        if not p or not p.photo_file_id:
            await update.message.reply_text("❌ No tienes perfil.", reply_markup=profile_kb(False))
        else:
            await update.message.reply_photo(
                photo=p.photo_file_id,
                caption=(
                    f"👤 {p.fullname}\n🌎{p.country}\n🏙️{p.city}\n"
                    f"⚧️{p.gender}\n🔎{p.pref_gender}\n"
                    f"🔗@{p.instagram or '—'}\n\n📝{p.description}"
                ),
                reply_markup=profile_kb(True)
            )
        return PROFILE_MENU
    if text=="❌ Borrar mi perfil":
        await update.message.reply_text("⚠️ Confirma Sí o No.")
        context.user_data["confirm_delete"]=True
        return PROFILE_MENU
    if context.user_data.get("confirm_delete"):
        if text.lower() in ("sí","si"):
            db.delete_profile(uid)
            await update.message.reply_text("🗑️ Perfil borrado.", reply_markup=main_kb(db, uid))
        else:
            await update.message.reply_text("✅ Cancelado.", reply_markup=profile_kb(True))
        context.user_data.pop("confirm_delete",None)
        return PROFILE_MENU
    if text=="🔙 Menú principal":
        await update.message.reply_text("🔙 Menú.", reply_markup=main_kb(db, uid))
        return MENU
    await update.message.reply_text("❌ Inválido.", reply_markup=profile_kb(db.has_profile(uid)))
    return PROFILE_MENU

async def perfil_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❗ Envía foto.")
        return PHOTO
    context.user_data['photo']=update.message.photo[-1].file_id
    await update.message.reply_text("📝 Envía descripción.")
    return DESC

async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description']=update.message.text
    await update.message.reply_text("🔗 Instagram o —.")
    return INSTA

async def perfil_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['instagram']=update.message.text.strip() or ""
    await update.message.reply_text("⚧️ Género.")
    return GENDER

async def perfil_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender']=update.message.text
    await update.message.reply_text("🔎 Pref. de género.")
    return PREF_GENDER

async def perfil_pref_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pref_gender']=update.message.text
    await update.message.reply_text("🌎 País.")
    return COUNTRY

async def perfil_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['country']=update.message.text
    await update.message.reply_text("🏙️ Ciudad.")
    return CITY

async def perfil_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; d=context.user_data; db=context.bot_data["db"]
    db.save_profile(uid,
        photo_file_id=d['photo'],
        description=d['description'],
        instagram=d['instagram'],
        gender=d['gender'],
        pref_gender=d['pref_gender'],
        country=d['country'],
        city=update.message.text
    )
    await update.message.reply_text("✅ Perfil guardado.", reply_markup=main_kb(db, uid))
    context.user_data.clear()
    return MENU

# — Búsqueda & Like —

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; db=context.bot_data["db"]
    context.user_data['candidates']=db.get_potential_matches(uid)
    context.user_data['idx']=0
    if not context.user_data['candidates']:
        await update.message.reply_text("🚫 No hay perfiles.", reply_markup=main_kb(db, uid))
        return MENU
    return await show_next(update, context)

async def show_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx=context.user_data['idx']; cand=context.user_data['candidates'][idx]
    await update.message.reply_photo(
        photo=cand.photo_file_id,
        caption=f"👤 {cand.fullname}\n🌎{cand.country}\n🏙️{cand.city}\n\n📝{cand.description}",
        reply_markup=search_inline_kb()
    )
    return SEARCH

async def search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    db=context.bot_data["db"]; uid=q.from_user.id
    idx=context.user_data['idx']; cand=context.user_data['candidates'][idx]
    if q.data=="search_like":
        me=db.get_profile(uid)
        await context.bot.send_photo(
            chat_id=cand.id,
            photo=me.photo_file_id,
            caption=(
                f"🎉 ¡A *{me.fullname}* le ha gustado tu perfil!\n\n"
                f"👤 {me.fullname}\n🌎{me.country}\n🏙️{me.city}\n\n📝{me.description}"
            ),
            reply_markup=notify_inline_kb(uid),
            parse_mode="Markdown"
        )
    context.user_data['idx']+=1
    if context.user_data['idx']>=len(context.user_data['candidates']):
        await q.edit_message_caption(caption=q.message.caption+"\n\n🚫 Se acabaron",reply_markup=None)
        await context.bot.send_message(chat_id=uid,text="🔙 Menú",reply_markup=back_kb())
        return MENU
    await q.delete_message()
    return await show_next(update, context)

# — Super Like directo —

async def super_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; db=context.bot_data["db"]
    if not db.use_super_like(uid):
        await update.message.reply_text("❌ Sin SL. Compra más.", reply_markup=main_kb(db, uid))
        return MENU
    # enviamos primer candidato directamente
    context.user_data['candidates']=db.get_potential_matches(uid)
    context.user_data['idx']=0
    if not context.user_data['candidates']:
        await update.message.reply_text("🚫 No hay perfiles.", reply_markup=main_kb(db, uid))
        return MENU
    idx=context.user_data['idx']; cand=context.user_data['candidates'][idx]
    me=db.get_profile(uid)
    await context.bot.send_photo(
        chat_id=cand.id, photo=me.photo_file_id,
        caption=(
            f"💥 Tienes un Super Like de *{me.fullname}*!\n\n"
            f"👤 {me.fullname}\n🌎{me.country}\n🏙️{me.city}\n\n📝{me.description}"
        ), reply_markup=contact_inline(uid), parse_mode="Markdown"
    )
    await update.message.reply_text("✅ SL enviado. Sin confirmación.\n🔙 Menú",reply_markup=main_kb(db, uid))
    return MENU

# — Confirmación match —

async def notify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    data,liker= q.data.split(":"); liker=int(liker)
    receiver=q.from_user.id; db=context.bot_data["db"]
    if data=="notify_like":
        await q.edit_message_caption(caption=q.message.caption+"\n\n🎉 Match!",reply_markup=contact_inline(liker))
        other=db.get_profile(receiver)
        await context.bot.send_photo(
            chat_id=liker,photo=other.photo_file_id,
            caption=(
                f"🎉 ¡Match mutuo con @{other.id}!\n"
                f"👤 {other.fullname}\n🌎{other.country}\n🏙️{other.city}\n\n📝{other.description}"
            ),reply_markup=contact_inline(receiver)
        )
    else:
        await q.edit_message_text("❌ Cerrado",reply_markup=None)

# — Compra Super Likes —
async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    uid=q.from_user.id; db=context.bot_data["db"]
    if q.data=="buy_1":
        db.purchase_super_likes(uid,1); text="✅ 1 SL comprado."
    elif q.data=="buy_5":
        db.purchase_super_likes(uid,5); text="✅ 5 SL comprados."
    else:
        db.purchase_super_likes(uid,10); text="✅ 10 SL comprados."
    credits=db.get_user(uid).super_likes
    await q.edit_message_text(f"{text}\n🎉 Tienes {credits} SL.",reply_markup=None)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; db=context.bot_data["db"]
    await update.message.reply_text("👋 Cancelado.",reply_markup=main_kb(db, uid))
    return ConversationHandler.END

def main():
    app=ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.bot_data["db"]=Database(config.DB_URL)

    conv=ConversationHandler(
        entry_points=[CommandHandler("start",start)],
        states={
            MENU:         [MessageHandler(filters.TEXT&~filters.COMMAND,menu_choice)],
            PROFILE_MENU: [MessageHandler(filters.TEXT&~filters.COMMAND,profile_menu)],
            PHOTO:        [MessageHandler(filters.PHOTO,perfil_photo)],
            DESC:         [MessageHandler(filters.TEXT&~filters.COMMAND,perfil_description)],
            INSTA:        [MessageHandler(filters.TEXT&~filters.COMMAND,perfil_instagram)],
            GENDER:       [MessageHandler(filters.TEXT&~filters.COMMAND,perfil_gender)],
            PREF_GENDER:  [MessageHandler(filters.TEXT&~filters.COMMAND,perfil_pref_gender)],
            COUNTRY:      [MessageHandler(filters.TEXT&~filters.COMMAND,perfil_country)],
            CITY:         [MessageHandler(filters.TEXT&~filters.COMMAND,perfil_city)],
            SEARCH:       [CallbackQueryHandler(search_callback,pattern="^search_")],
            SUPER:        [MessageHandler(filters.TEXT&~filters.COMMAND,lambda u,c:MENU)],
        },
        fallbacks=[CommandHandler("cancelar",cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("grant_super",grant_super))
    app.add_handler(CallbackQueryHandler(notify_callback,pattern="^notify_"))
    app.add_handler(CallbackQueryHandler(buy_callback,pattern="^buy_"))
    app.add_handler(CommandHandler("help",help_command))

    logger.info("🤖 Bot iniciado correctamente")
    app.run_polling()

if __name__=="__main__":
    main()
