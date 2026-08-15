from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from utils.bdft_env import BDFTBot, BDFTUser, BDFTHTTP
from utils.formatter import to_small_caps
from config import config

router = Router()

async def get_env(message: types.Message):
    return {
        "u": message.from_user.id,
        "bot": BDFTBot(message.bot),
        "Bot": BDFTBot(message.bot),
        "User": BDFTUser(),
        "message": message
    }

# --- Reactions ---
@router.message(Command("reaction"))
async def cmd_reaction(message: types.Message):
    env = await get_env(message)
    u, bot = env['u'], env['bot']
    
    reactions = ['👍', '👎', '❤', '🔥', '🥰', '👏', '😁', '🤔', '🤯', '🤬', '😢', '🎉', '🤩', '🤮', '💩', '🙏', '👌', '🕊', '🤡', '🥱', '🥴', '😍', '🐳', '❤️‍🔥', '🌚', '🌭', '💯', '🤣', '⚡', '🍌', '🏆', '💔', '🤨', '😐', '🍓', '🍾', '💋', '🖕', '😈', '😴', '😭', '🤓', '👻', '👨‍💻', '👀', '🎃', '🙈', '😇', '😨', '🤝', '✍️', '🎅', '🫡', '🆒', '💘', '🙉', '🦄', '😘', '💊', '🙊']
    
    kb = InlineKeyboardBuilder()
    for reaction in reactions:
        kb.add(InlineKeyboardButton(text=reaction, callback_data=f"react_{reaction}"))
    kb.adjust(6) # 6 buttons per row
    
    await message.answer(
        f"<b>🎯 {to_small_caps('Select The Desired Reaction')}</b>\n\nℹ️ <i>{to_small_caps('Note: To Request Some Reactions, The Desired Reaction Must Be Added Manually Once For The Post!')}</i>", 
        parse_mode="html", 
        reply_markup=kb.as_markup()
    )

@router.callback_query(F.data.startswith("react_"))
async def cb_reaction(callback: types.CallbackQuery):
    reaction = callback.data.split("_")[1]
    await callback.answer(f"Reaction {reaction} selected!")
    await callback.message.edit_text(f"✅ <b>{to_small_caps('Reaction')} {reaction} {to_small_caps('has been set!')}</b>", parse_mode="html")

# --- Polls & Votes ---
@router.message(Command("poll"))
async def cmd_poll(message: types.Message):
    # Logic from poll_22.py/vote_50.py
    await message.answer("<b>🗳️ Create a Poll or Vote</b>\n\nUsage: `/poll Question | Option1 | Option2`", parse_mode="html")

@router.message(F.text == to_small_caps("🗳️ Vote"))
async def cmd_vote(message: types.Message):
    await message.answer("<b>🗳️ Active Community Votes</b>\n\nCurrently no active votes.", parse_mode="html")
