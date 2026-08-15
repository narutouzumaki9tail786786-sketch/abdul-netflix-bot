import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from handlers import user, services, admin, store, economy, broadcast, interactions, payments
from middlewares.force_join import ForceJoinMiddleware
from utils.db_manager import db

# --- PREMIUM EMOJI MONKEY PATCH ---
from aiogram.types import InlineKeyboardButton, KeyboardButton, TelegramObject

# Allow extra fields in Pydantic models
InlineKeyboardButton.model_config.update({"extra": "allow"})
KeyboardButton.model_config.update({"extra": "allow"})

# Ensure extra fields like icon_custom_emoji_id are included in the JSON dump
_old_dump = TelegramObject.model_dump
def _new_dump(self, *args, **kwargs):
    # Ensure extras are included in Pydantic V2 dump
    kwargs['exclude_none'] = True
    d = _old_dump(self, *args, **kwargs)
    # Support for icon_custom_emoji_id and native style (Bot API 9.4)
    if hasattr(self, 'icon_custom_emoji_id') and self.icon_custom_emoji_id:
        d['icon_custom_emoji_id'] = self.icon_custom_emoji_id
    elif hasattr(self, 'custom_emoji_id') and self.custom_emoji_id:
        d['icon_custom_emoji_id'] = self.custom_emoji_id
        
    if hasattr(self, 'style') and self.style:
        d['style'] = self.style
    return d
TelegramObject.model_dump = _new_dump
# ----------------------------------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def main():
    # Initialize Bot and Dispatcher
    bot = Bot(token=config.BOT_TOKEN)
    
    # We use MemoryStorage for FSM
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register Middlewares
    dp.message.middleware(ForceJoinMiddleware())

    # Include routers
    dp.include_router(user.router)
    dp.include_router(services.router)
    dp.include_router(admin.router)
    dp.include_router(store.router)
    dp.include_router(payments.router)
    dp.include_router(economy.router)
    dp.include_router(broadcast.router)
    dp.include_router(interactions.router)

    # Global Middleware to track users
    @dp.message.outer_middleware()
    async def track_user_middleware(handler, event, data):
        user_id = str(event.from_user.id)
        # Ensure user exists in broadcast list
        broadcast_list = await db.get_bot_data("broadcast", [])
        if user_id not in broadcast_list:
            broadcast_list.append(user_id)
            await db.save_bot_data("broadcast", broadcast_list)
        return await handler(event, data)

    # Start polling
    logger.info("Starting Netflix Bot...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
