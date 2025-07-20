# main.py

import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
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

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Inicializamos la base de datos
db = Database(config.DB_URL)

# Estados para ConversationHandler de perfil
DESC, INSTA, GENDER, COUNTRY, CITY = range(5)

def main_keyboard(is_premium: bool = False, is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton("👥 Emparejar")],
        [KeyboardButton("🔔 Promociones")],
    ]
    if not is_premium:
        buttons.append([KeyboardButton("💎 Hacerme Premium")])
        buttons.append([KeyboardButton("🚫 No recibir Promos")])
    buttons.append([KeyboardButton("📄 Perfil")])
    if is_admin:
        buttons.append([KeyboardButton("📣 Enviar Promos")])
    buttons.append([KeyboardButton("🛑 Salir")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    is_prem = db.is_premium(user.id)
    is_admin = (user.id == config.ADMIN_ID)
    text = (
        "Leo: ¡Ligar. Citas y amigos! 💕\n"
        "Ayuda 👉 @leomatchbot_help\n"
        "Compra publicidad 👉 @ADinsidebot\n\n"
        f"¡Hola, {user.first_name}! 🤖\n"
        "Bienvenido a LeoMatch Bot. Elige una opción del teclado:"
    )
    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(is_prem, is_admin),
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usa los botones del teclado para navegar por las opciones. 🤖\n"
        "Para editar tu perfil usa /perfil\n"
        "Para cancelar un flujo, envía /cancelar"
    )

# Manejo general de texto (botones principales)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    is_prem = db.is_premium(user_id)
    is_admin = (user_id == config.ADMIN_ID)

    # Broadcast flow
    if context.user_data.get("broadcasting"):
        msg = text
        for uid in db.get_all_user_ids():
            await context.bot.send_message(chat_id=uid, text=msg)
        context.user_data.pop("broadcasting")
        await update.message.reply_text(
            "✅ Promoción enviada a todos los usuarios.",
            reply_markup=main_keyboard(is_prem, is_admin),
        )
        return

    if text == "👥 Emparejar":
        matches = db.get_matches(version=is_prem)
        reply = "Tu lista de matches:\n" + "\n".join(matches) if matches else "No hay matches aún."

    elif text == "🔔 Promociones":
        reply = (
            "Para recibir promociones, primero hazte Premium con 💎 Hacerme Premium"
            if not is_prem else "No hay promociones nuevas 🤝"
        )

    elif text == "💎 Hacerme Premium":
        db.set_premium(user_id)
        reply = "¡Felicidades! Ahora eres usuario Premium 🎉"

    elif text == "🚫 No recibir Promos":
        db.set_no_promos(user_id)
        reply = "Has elegido no recibir más promociones. Puedes volver con /start."

    elif text == "📄 Perfil":
        return await perfil_start(update, context)

    elif text == "📣 Enviar Promos" and is_admin:
        context.user_data["broadcasting"] = True
        await update.message.reply_text(
            "✉️ Envíame el mensaje que deseas enviar a todos los usuarios:",
            reply_markup=main_keyboard(is_prem, is_admin),
        )
        return

    elif text == "🛑 Salir":
        db.unregister_user(user_id)
        reply = "Has salido. Si deseas volver, usa /start 👋"

    else:
        reply = "Opción no reconocida. Por favor, usa los botones del teclado."

    await update.message.reply_text(
        reply,
        reply_markup=main_keyboard(is_prem, is_admin),
    )

# ----------------- Flujo de perfil -----------------

async def perfil_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Por favor, envíame una breve descripción de tu perfil o /cancelar para salir:",
    )
    return DESC

async def perfil_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("¿Cuál es tu usuario de Instagram? (sin @):")
    return INSTA

async def perfil_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['instagram'] = update.message.text
    await update.message.reply_text(
        "Selecciona tu género:",
        reply_markup=ReplyKeyboardMarkup(
            [["Masculino"], ["Femenino"], ["Otro"], ["/cancelar"]],
            resize_keyboard=True,
        ),
    )
    return GENDER

async def perfil_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("¿En qué país vives?")
    return COUNTRY

async def perfil_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['country'] = update.message.text
    await update.message.reply_text("¿Y en qué ciudad o provincia?")
    return CITY

async def perfil_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    # Guardar en BD
    db.update_profile(
        update.effective_user.id,
        context.user_data['description'],
        context.user_data['instagram'],
        context.user_data['gender'],
        context.user_data['country'],
        context.user_data['city'],
    )
    # Mostrar resumen
    text = (
        "Perfil actualizado:\n"
        f"📝 {context.user_data['description']}\n"
        f"📸 https://instagram.com/{context.user_data['instagram']}\n"
        f"👤 {context.user_data['gender']}\n"
        f"📍 {context.user_data['city']}, {context.user_data['country']}"
    )
    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(db.is_premium(update.effective_user.id), update.effective_user.id==config.ADMIN_ID),
    )
    context.user_data.clear()
    return ConversationHandler.END

async def perfil_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Operación de perfil cancelada.",
        reply_markup=main_keyboard(db.is_premium(update.effective_user.id), update.effective_user.id==config.ADMIN_ID),
    )
    context.user_data.clear()
    return ConversationHandler.END

# ----------------- Arranque -----------------

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    perfil_conv = ConversationHandler(
        entry_points=[CommandHandler("perfil", perfil_start)],
        states={
            DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_description)],
            INSTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_instagram)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_gender)],
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_country)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, perfil_city)],
        },
        fallbacks=[CommandHandler("cancelar", perfil_cancel)],
    )
    app.add_handler(perfil_conv)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Iniciando LeoMatch Bot...")
    app.run_polling()
