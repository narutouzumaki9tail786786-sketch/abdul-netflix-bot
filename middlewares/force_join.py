from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, types
from aiogram.exceptions import TelegramBadRequest
from config import config
from utils.force_join import build_force_join_keyboard, get_all_force_join_items


class ForceJoinMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        # Check only for messages and callback queries
        if not isinstance(event, (types.Message, types.CallbackQuery)):
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if not user_id or event.from_user.is_bot:
            return await handler(event, data)
        
        # Skip check for admins
        if user_id in config.ADMINS:
            return await handler(event, data)

        # Skip check for the verification callback itself
        if isinstance(event, types.CallbackQuery) and event.data == "verify_join":
            return await handler(event, data)
        
        # Check membership in all channels
        force_join_items = await get_all_force_join_items()
        not_joined = []
        for item in force_join_items:
            channel = item["chat_id"]
            try:
                member = await event.bot.get_chat_member(chat_id=channel, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    not_joined.append(item)
            except TelegramBadRequest:
                not_joined.append(item)
            except Exception:
                continue

        if not_joined:
            # If it's a start command, we let the handler show the links
            if isinstance(event, types.Message) and event.text and event.text.startswith("/start"):
                data["not_joined"] = not_joined
                return await handler(event, data)
            
            # For everything else, block and show the join message
            kb = build_force_join_keyboard(force_join_items)
            
            error_text = "<tg-emoji emoji-id=\"5296258364655805333\">🎥</tg-emoji> <b>ᴅᴏɴ'ᴛ ᴍɪꜱꜱ ᴏᴜᴛ!</b>\n\nᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟꜱ ɴᴏᴡ ᴛᴏ ᴜɴʟᴏᴄᴋ <b>ꜰʀᴇᴇ ɴᴇᴛꜰʟɪx ᴘʀᴇᴍɪᴜᴍ</b> ᴀᴄᴄᴏᴜɴᴛꜱ!\n\nᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ ʙᴇʟᴏᴡ ᴀɴᴅ ᴄʟɪᴄᴋ ᴠᴇʀɪꜰʏ <tg-emoji emoji-id=\"6111827380915934490\">✅</tg-emoji>"
            
            # Use BDFTBot wrapper for easy media sending
            from utils.bdft_env import BDFTBot
            bot_wrapper = BDFTBot(event.bot)
            
            if config.START_MEDIA_TYPE == "photo":
                await bot_wrapper.sendPhoto(chat_id=user_id, photo=config.START_MEDIA, caption=error_text, reply_markup=kb)
            elif config.START_MEDIA_TYPE == "animation":
                await bot_wrapper.sendAnimation(chat_id=user_id, animation=config.START_MEDIA, caption=error_text, reply_markup=kb)
            elif config.START_MEDIA_TYPE == "video":
                await bot_wrapper.sendVideo(chat_id=user_id, video=config.START_MEDIA, caption=error_text, reply_markup=kb)
            else:
                await bot_wrapper.sendMessage(chat_id=user_id, text=error_text, reply_markup=kb)
                
            if isinstance(event, types.CallbackQuery):
                await event.answer()
            return # Stop propagation

        return await handler(event, data)
