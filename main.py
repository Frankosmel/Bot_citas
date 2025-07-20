# main.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
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

# Handler /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    keyboard = [
        [InlineKeyboardButton("👥 Emparejar", callback_data="match")],
        [InlineKeyboardButton("🔔 Promociones", callback_data="promotions")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"¡Hola, {user.first_name}! Bienvenido a LeoMatch 🤖\nElige una opción:",
        reply_markup=reply_markup,
    )

# Callback de botones
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "match":
        users = db.get_matches(version=db.is_premium(query.from_user.id))
        text = "Tu lista de matches:\n" + "\n".join(users) if users else "No hay matches aún."
        await query.edit_message_text(text)
    elif query.data == "promotions":
        if not db.is_premium(query.from_user.id):
            await query.edit_message_text("Para recibir promociones, hazte premium ✨")
        else:
            await query.edit_message_text("No hay promociones nuevas 🤝")

# Handler /premium
async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_premium(update.effective_user.id)
    await update.message.reply_text("¡Ahora eres premium! 🎉")

# Handler /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.unregister_user(update.effective_user.id)
    await update.message.reply_text("Has salido del bot. ¡Vuelve pronto! 👋")

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CallbackQueryHandler(button_handler))
    logger.info("🤖 Iniciando LeoMatch Bot...")
    app.run_polling()
