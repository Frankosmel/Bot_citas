# main.py

"""
✨ main.py
Punto de entrada de LeoMatch: registra handlers y arranca el bot.
"""

import logging
from aiogram import Bot, Dispatcher
from aiogram.utils import executor

from config import API_TOKEN
from register import register_handlers_register
from promotions import register_handlers_promotions
from match import register_handlers_match
from profile import register_handlers_profile
from admin import register_handlers_admin

# ─── Configuración de logging ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Instancia del Bot y Dispatcher ─────────────────────────────────────────
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ─── Registro de handlers ──────────────────────────────────────────────────
register_handlers_register(dp)
register_handlers_promotions(dp)
register_handlers_match(dp)
register_handlers_profile(dp)
register_handlers_admin(dp)
# Si más adelante agregas nuevos módulos (block, stats, etc.), los registras aquí

# ─── Arranque del polling ────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("🤖 Iniciando LeoMatch Bot...")
    executor.start_polling(dp, skip_updates=True)
