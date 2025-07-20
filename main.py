# main.py

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
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

def main_keyboard(is_premium: bool = False) -> ReplyKeyboardMarkup:
    """
    Construye el teclado principal según si el usuario es premium o no.
    """
    buttons = [
        [KeyboardButton("👥 Emparejar")],
        [KeyboardButton("🔔 Promociones")]
    ]
    if not is_premium:
        buttons.append([KeyboardButton("💎 Hacerme Premium")])
    buttons.append([KeyboardButton("🛑 Salir")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# Handler /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.full_name)
    is_prem = db.is_premium(user.id)
    text = (
        f"¡Hola, {user.first_name}! 🤖\n"
        "Bienvenido a LeoMatch Bot. Elige una opción del teclado:"
    )
    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(is_prem),
    )

# Handler de mensajes de texto
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    is_prem = db.is_premium(user_id)

    if text == "👥 Emparejar":
        users = db.get_matches(version=is_prem)
        reply = (
            "Tu lista de matches:\n" + "\n".join(users)
            if users else "No hay matches disponibles aún."
        )

    elif text == "🔔 Promociones":
        if not is_prem:
            reply = "Para recibir promociones, primero hazte Premium con 💎 Hacerme Premium"
        else:
            reply = "No hay promociones nuevas por el momento 🤝"

    elif text == "💎 Hacerme Premium":
        db.set_premium(user_id)
        reply = "¡Felicidades! Ahora eres usuario Premium 🎉"

    elif text == "🛑 Salir":
        db.unregister_user(user_id)
        reply = "Has salido. Si deseas volver, usa /start 👋"

    else:
        reply = "Opción no reconocida. Por favor, usa los botones del teclado."

    # En cada respuesta, mostramos de nuevo el teclado actualizado
    await update.message.reply_text(
        reply,
        reply_markup=main_keyboard(is_prem),
    )

# Handler /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usa los botones del teclado para navegar por las opciones. 🤖"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🤖 Iniciando LeoMatch Bot...")
    app.run_polling()
