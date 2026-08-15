from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.bdft_env import BDFTBot, BDFTUser, BDFTLibs
from utils.db_manager import db
from config import config

router = Router()

class TransferStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()

async def get_env(message: types.Message):
    return {
        "u": message.from_user.id,
        "bot": BDFTBot(message.bot),
        "Bot": BDFTBot(message.bot),
        "User": BDFTUser(),
        "libs": BDFTLibs(),
        "message": message
    }

# --- Transfer Logic ---

@router.message(F.text == "💸 ᴛʀᴀɴsꜰᴇʀ")
@router.message(Command("transfer"))
async def cmd_transfer_start(message: types.Message, state: FSMContext):
    env = await get_env(message)
    u, bot = env['u'], env['bot']
    
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="⛔ ᴄᴀɴᴄᴇʟ")
    
    await bot.sendMessage(
        chat_id=u, 
        text=f"👀 <b>ᴇɴᴛᴇʀ ᴛʜᴇ ᴜꜱᴇʀ ɪᴅ ᴏꜰ ʏᴏᴜʀ ꜰʀɪᴇɴᴅ ᴡʜᴏᴍ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴛʀᴀɴꜱꜰᴇʀ ʏᴏᴜʀ ᴄᴏɪɴꜱ</b>", 
        parse_mode="html", 
        reply_markup=kb.as_markup(resize_keyboard=True, input_field_placeholder="🍿 Choose a Netflix plan below...")
    )
    await state.set_state(TransferStates.waiting_for_user_id)

@router.message(TransferStates.waiting_for_user_id)
async def process_transfer_user_id(message: types.Message, state: FSMContext):
    if message.text == "⛔ ᴄᴀɴᴄᴇʟ":
        await state.clear()
        await message.answer("❌ Transfer cancelled.")
        return

    env = await get_env(message)
    u, bot, User = env['u'], env['bot'], env['User']

    try:
        target_id = int(message.text)
    except ValueError:
        await message.answer("⚠️ Please enter a numeric User ID.")
        return

    if target_id == u:
        await message.answer("❌ You cannot transfer points to yourself!")
        return

    # Check if target user exists
    target_exists = await User.getData("balance", target_id)
    if target_exists is None:
        await message.answer("❌ User not found in our database.")
        return

    await state.update_data(target_id=target_id)
    await message.answer(f"✅ Target User: <code>{target_id}</code>\n\n💰 <b>Enter the amount you want to transfer:</b>", parse_mode="html")
    await state.set_state(TransferStates.waiting_for_amount)

@router.message(TransferStates.waiting_for_amount)
async def process_transfer_amount(message: types.Message, state: FSMContext):
    if message.text == "⛔ ᴄᴀɴᴄᴇʟ":
        await state.clear()
        await message.answer("❌ Transfer cancelled.")
        return

    env = await get_env(message)
    u, bot, User = env['u'], env['bot'], env['User']
    data = await state.get_data()
    target_id = data['target_id']

    try:
        amount = int(message.text)
    except ValueError:
        await message.answer("⚠️ Please enter a numeric amount.")
        return

    if amount < 1:
        await message.answer("⚠️ Minimum transfer amount is 1 Point.")
        return

    balance = await User.getData("balance", u) or 0
    balance = int(balance)

    if amount > balance:
        await message.answer("❌ You don't have enough points for this transfer.")
        return

    # Execute transfer
    await User.saveData("balance", balance - amount, u)
    target_bal = await User.getData("balance", target_id) or 0
    await User.saveData("balance", int(target_bal) + amount, target_id)

    await state.clear()

    # Success notification to sender
    success_msg = (
        f"<b>✅ ᴛʀᴀɴꜱꜰᴇʀ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ!</b>\n\n"
        f"👤 ꜱᴇɴᴛ ᴛᴏ: <code>{target_id}</code>\n"
        f"🎟 ᴀᴍᴏᴜɴᴛ: <b>{amount} ᴘᴏɪɴᴛꜱ</b>\n\n"
        f"<i>ᴘᴏɪɴᴛꜱ ʜᴀᴠᴇ ʙᴇᴇɴ ᴅᴇᴅᴜᴄᴛᴇᴅ ꜰʀᴏᴍ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ.</i>"
    )
    await bot.sendPhoto(
        chat_id=u, 
        photo="https://graph.org/file/860c699451444e382792f.jpg", 
        caption=success_msg, 
        parse_mode="html"
    )

    # Notification to receiver
    try:
        await bot.sendMessage(
            chat_id=target_id, 
            text=f"<b>🎁 You received {amount} Points from a friend!</b>", 
            parse_mode="html"
        )
    except:
        pass

# --- Withdrawal Logic ---

@router.message(Command("withdraw"))
async def cmd_withdraw(message: types.Message):
    env = await get_env(message)
    u, bot, User = env['u'], env['bot'], env['User']
    
    balance = await User.getData("balance", u) or 0
    if int(balance) < 3:
        await message.answer("❌ <b>ʏᴏᴜ ɴᴇᴇᴅ ᴀᴛ ʟᴇᴀꜱᴛ 3 ᴘᴏɪɴᴛꜱ ᴛᴏ ᴡɪᴛʜᴅʀᴀᴡ ᴀ ɴᴇᴛꜰʟɪx ᴀᴄᴄᴏᴜɴᴛ.</b>", parse_mode="html")
        return

    # Send Notification to Log Channel
    log_text = (
        f"<b>📥 ɴᴇᴡ ᴡɪᴛʜᴅʀᴀᴡᴀʟ ʀᴇQᴜᴇꜱᴛ</b>\n\n"
        f"👤 ᴜꜱᴇʀ: <code>{message.from_user.full_name}</code>\n"
        f"🆔 ɪᴅ: <code>{u}</code>\n"
        f"💰 ʙᴀʟᴀɴᴄᴇ: <code>{balance} ᴘᴏɪɴᴛꜱ</code>\n\n"
        f"⚠️ <b>ꜱᴛᴀᴛᴜꜱ: ᴘᴇɴᴅɪɴɢ</b>\n\n"
        f"<i>ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪᴛʜ ᴀ ᴠɪᴅᴇᴏ ᴏʀ ʟɪɴᴋ ᴛᴏ ᴄᴏᴍᴘʟᴇᴛᴇ ᴛʜᴇ ᴏʀᴅᴇʀ.</i>"
    )
    
    try:
        await message.bot.send_message(chat_id=config.LOG_CHANNEL_ID, text=log_text, parse_mode="html")
        await message.answer("✅ <b>ʏᴏᴜʀ ᴡɪᴛʜᴅʀᴀᴡᴀʟ ʀᴇQᴜᴇꜱᴛ ʜᴀꜱ ʙᴇᴇɴ ꜱᴇɴᴛ ᴛᴏ ᴀᴅᴍɪɴꜱ!</b>\n\nᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ꜰᴏʀ ᴘʀᴏᴄᴇꜱꜱɪɴɢ.", parse_mode="html")
    except Exception as e:
        await message.answer("❌ ᴇʀʀᴏʀ ꜱᴇɴᴅɪɴɢ ʀᴇQᴜᴇꜱᴛ. ᴘʟᴇᴀꜱᴇ ᴄᴏɴᴛᴀᴄᴛ ꜱᴜᴘᴘᴏʀᴛ.")


