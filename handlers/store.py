from aiogram import Router, types, F
from aiogram.filters import Command
from utils.bdft_env import BDFTBot, BDFTUser, BDFTLibs
from utils.db_manager import db
from config import config

router = Router()

async def get_env(message: types.Message):
    return {
        "u": message.from_user.id,
        "bot": BDFTBot(message.bot),
        "Bot": BDFTBot(message.bot),
        "User": BDFTUser(),
        "libs": BDFTLibs(),
        "message": message
    }

@router.message(Command("redeem"))
async def cmd_redeem(message: types.Message):
    env = await get_env(message)
    u, bot, Bot, User, libs = env['u'], env['bot'], env['Bot'], env['User'], env['libs']

    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Usage: `/redeem <YOUR_CODE>`")
        return

    code = args[1].upper()
    
    # Check if coupon exists
    coupon_val = await Bot.getData(f"Coupon={code}")
    
    if coupon_val is None:
        await bot.sendMessage(u, "<b>❌ Invalid Redeem Code</b>", parse_mode="html")
    elif coupon_val == "null":
        await bot.sendMessage(u, "<b>⚠️ This code has already been redeemed!</b>", parse_mode="html")
    else:
        # Valid code
        points = int(coupon_val)
        current_bal = await User.getData("balance", u) or 0
        
        # Update balance
        await User.saveData("balance", int(current_bal) + points, u)
        
        # Mark as used
        await Bot.saveData(f"Coupon={code}", "null")
        
        now = BDFTLibs.dateandtime.now("Asia/kolkata")
        
        success_msg = (
            f"<b><tg-emoji emoji-id=\"6026162407066309019\">🎉</tg-emoji> ꜱᴜᴄᴄᴇꜱꜱ!</b>\n\n"
            f"<tg-emoji emoji-id=\"5350452584119279096\">💰</tg-emoji> <b>{points} ᴘᴏɪɴᴛꜱ</b> ʜᴀᴠᴇ ʙᴇᴇɴ ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ.\n"
            f"<tg-emoji emoji-id=\"6035084557378654059\">👤</tg-emoji> ɴᴇᴡ ʙᴀʟᴀɴᴄᴇ: <b>{int(current_bal) + points} ᴘᴏɪɴᴛꜱ</b>\n\n"
            f"<tg-emoji emoji-id=\"5451732530048802485\">⏰</tg-emoji> ᴛɪᴍᴇ: <code>{now['time']}</code>"
        )
        
        # Admin notification (Optional but good)
        # try: await bot.sendMessage(config.ADMIN_ID, f"🔔 User {u} redeemed coupon {code} for {points} points.")
        # except: pass

        await bot.sendMessage(u, success_msg, parse_mode="html")

@router.message(F.text == "ʙᴜʏ ᴄᴏɪɴs")
async def cmd_buy_coins(message: types.Message):
    await send_buy_coins_menu(message)

async def send_buy_coins_menu(message: types.Message):
    buy_text = (
        "<tg-emoji emoji-id=\"5267300544094948794\">💳</tg-emoji> <b>ʙᴜʏ ɴᴇᴛꜰʟɪx ᴘᴏɪɴᴛꜱ</b>\n\n"
        "• <b>3 ᴘᴏɪɴᴛꜱ</b> = 1 ᴛᴏᴋᴇɴ ʟᴏɢɪɴ\n"
        "• <b>5 ᴘᴏɪɴᴛꜱ</b> = 1 ᴇᴍᴀɪʟ/ᴘᴀꜱꜱ ʟᴏɢɪɴ\n\n"
        "<tg-emoji emoji-id=\"5350452584119279096\">💎</tg-emoji> <b>ᴘʀɪᴄᴇ ʟɪꜱᴛ:</b>\n"
        "• 1 ᴀᴄᴄᴏᴜɴᴛ (3 ᴘᴏɪɴᴛꜱ): ₹50 / $0.60\n"
        "• 3 ᴀᴄᴄᴏᴜɴᴛꜱ (9 ᴘᴏɪɴᴛꜱ): ₹130 / $1.50\n"
        "• 5 ᴀᴄᴄᴏᴜɴᴛꜱ (15 ᴘᴏɪɴᴛꜱ): ₹200 / $2.40\n\n"
        "<tg-emoji emoji-id=\"5780405967527089720\">📢</tg-emoji> <b>ʜᴏᴡ ᴛᴏ ʙᴜʏ:</b>\n"
        "ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴍᴇꜱꜱᴀɢᴇ ᴛʜᴇ ᴀᴅᴍɪɴ ᴀɴᴅ ɢᴇᴛ ʏᴏᴜʀ ᴘᴏɪɴᴛꜱ ɪɴꜱᴛᴀɴᴛʟʏ ᴠɪᴀ ᴜᴘɪ ᴏʀ ʙɪɴᴀɴᴄᴇ."
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="USDT Auto Pay", callback_data="buy_points_crypto", icon_custom_emoji_id="6282671941476164461"))
    kb.add(InlineKeyboardButton(text="Telegram Stars", callback_data="buy_points_stars", icon_custom_emoji_id="6109340839664686978"))
    kb.add(InlineKeyboardButton(text="ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url="https://t.me/apifounder", icon_custom_emoji_id="6181214480253325862")) # Admin icon
    kb.adjust(1)
    
    await message.answer(buy_text, parse_mode="html", reply_markup=kb.as_markup())
