import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.bdft_env import BDFTBot, BDFTUser
from utils.db_manager import db
from config import config

router = Router()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()

async def get_env(message: types.Message):
    return {
        "u": message.from_user.id,
        "bot": BDFTBot(message.bot),
        "Bot": BDFTBot(message.bot),
        "User": BDFTUser(),
        "message": message
    }

@router.message(Command("broadcast"))
@router.message(F.text == "📢 ʙʀᴏᴀᴅᴄᴀꜱᴛ")
async def cmd_broadcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        return

    await message.answer(f"<b>🎙️ sᴇɴᴅ ᴀɴʏ ᴍᴇssᴀɢᴇ (ᴛᴇxᴛ, ᴘʜᴏᴛᴏ, ᴠɪᴅᴇᴏ, ᴇᴛᴄ.) ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ.</b>\n\nᴛᴏ ᴄᴀɴᴄᴇʟ: /cancel", parse_mode="html")
    await state.set_state(BroadcastStates.waiting_for_message)

@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("<b>❌ Broadcast Cancelled</b>", parse_mode="html")
        return

    all_users = await db.get_all_users()
    await message.answer(f"📢 <b>sᴛᴀʀᴛɪɴɢ ʙʀᴏᴀᴅᴄᴀsᴛ ᴛᴏ {len(all_users)} ᴜsᴇʀs...</b>", parse_mode="html")
    
    await state.clear()
    
    success = 0
    fail = 0
    
    for user_id in all_users:
        try:
            # Re-using the message directly (copying)
            await message.copy_to(user_id)
            success += 1
            await asyncio.sleep(0.05) # Prevent flood
        except:
            fail += 1
            
    result_text = (
        f"<b>✅ ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏɴᴇ</b>\n\n"
        f"👥 ᴛᴏᴛᴀʟ: {len(all_users)}\n"
        f"✅ sᴜᴄᴄᴇss: {success}\n"
        f"❌ ꜰᴀɪʟᴇᴅ: {fail}"
    )
    await message.answer(result_text, parse_mode="html")
