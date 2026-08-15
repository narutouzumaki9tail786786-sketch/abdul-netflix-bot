from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
from utils.bdft_env import BDFTBot, BDFTUser, BDFTHTTP, BDFTLibs, bunchify
from utils.db_manager import db
from utils.force_join import build_force_join_keyboard, get_all_force_join_items
from utils.formatter import to_small_caps
from config import config

router = Router()

NETFLIX_HELP_BUTTON = "ɴᴇᴛꜰʟɪx ʜᴇʟᴘ"

NETFLIX_HELP_TEXT = (
    "<tg-emoji emoji-id=\"5296258364655805333\">🎬</tg-emoji> <b>ɴᴇᴛꜰʟɪx ʟɪɴᴋ / ɴꜰᴛᴏᴋᴇɴ ʜᴇʟᴘ</b>\n\n"
    "<blockquote expandable=True>"
    "<b>ɪꜰ ʟɪɴᴋ ᴏᴘᴇɴꜱ “ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ”:</b>\n"
    "1. ᴄʟᴇᴀʀ ɴᴇᴛꜰʟɪx ᴀᴘᴘ ᴅᴀᴛᴀ / ᴄᴀᴄʜᴇ.\n"
    "   • ᴀɴᴅʀᴏɪᴅ: Settings > Apps > Netflix > Storage > Clear Data\n"
    "   • ɪᴘʜᴏɴᴇ: Delete Netflix app, install again\n"
    "   • ᴘᴄ/ʙʀᴏᴡꜱᴇʀ: Clear netflix.com site data or open incognito\n"
    "2. ᴄʟᴏꜱᴇ ɴᴇᴛꜰʟɪx ᴄᴏᴍᴘʟᴇᴛᴇʟʏ, ᴛʜᴇɴ ᴏᴘᴇɴ ᴛʜᴇ ꜰʀᴇꜱʜ ʟɪɴᴋ.\n"
    "3. ᴅᴏɴ'ᴛ ᴜꜱᴇ ᴏʟᴅ / ʀᴇᴜꜱᴇᴅ ʟɪɴᴋꜱ. ɪꜰ ɪᴛ ᴇxᴘɪʀᴇᴅ, ɢᴇᴛ ᴀ ɴᴇᴡ ʟɪɴᴋ.\n\n"
    "<b>ɴꜰᴛᴏᴋᴇɴ ᴛɪᴍᴇ ʟɪᴍɪᴛ:</b>\n"
    "• English: Use the NFToken link within 15 minutes. After 15 minutes it can expire and show an error.\n"
    "• Hinglish: NFToken link 15 minutes ke andar use karo. 15 min ke baad expire/error aa sakta hai.\n"
    "• If expired, ask admin in DM (@apifounder) for a fresh link.\n\n"
    "<b>ᴄᴏᴍᴍᴏɴ ɴꜰᴛᴏᴋᴇɴ ꜰɪxᴇꜱ:</b>\n"
    "• ᴛᴜʀɴ ᴏꜰꜰ ᴠᴘɴ / ᴘʀᴏxʏ / ᴀᴅʙʟᴏᴄᴋ ʙᴇꜰᴏʀᴇ ᴏᴘᴇɴɪɴɢ ʟɪɴᴋ.\n"
    "• ᴜᴘᴅᴀᴛᴇ ɴᴇᴛꜰʟɪx ᴀᴘᴘ, ᴏʀ ᴛʀʏ ᴀɴᴏᴛʜᴇʀ ʙʀᴏᴡꜱᴇʀ.\n"
    "• ᴛᴠ ʟɪɴᴋ ɴᴏᴛ ᴡᴏʀᴋɪɴɢ? ʀᴇꜱᴛᴀʀᴛ ᴛᴠ / ɴᴇᴛꜰʟɪx ᴀᴘᴘ ᴀɴᴅ ᴛʀʏ ᴀ ɴᴇᴡ ʟɪɴᴋ.\n"
    "• ɪꜰ ᴀᴄᴄᴏᴜɴᴛ ꜱʜᴏᴡꜱ ᴇxᴘɪʀᴇᴅ / ʟᴏɢɢᴇᴅ ᴏᴜᴛ, ꜱᴇɴᴅ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ ᴘʀᴏᴏꜰ ᴛᴏ @apifounder ꜰᴏʀ ʀᴇᴘʟᴀᴄᴇᴍᴇɴᴛ."
    "</blockquote>"
)


class UserSettingsStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_wallet = State()


async def get_env(message: types.Message):
    return {
        "u": message.from_user.id,
        "bot": BDFTBot(message.bot),
        "Bot": BDFTBot(message.bot),
        "User": BDFTUser(),
        "HTTP": BDFTHTTP(),
        "libs": BDFTLibs(),
        "message": message
    }

@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject, not_joined: list = None):
    env = await get_env(message)
    u, bot, Bot, User, message = env['u'], env['bot'], env['Bot'], env['User'], env['message']
    
    # --- Referral Storage (Capture ID before Force Join Block) ---
    is_joined = await User.getData("is_started", u)
    if not is_joined:
        # Check for deep-link referral argument
        if command.args and command.args.isdigit():
            ref_id = int(command.args)
            if ref_id != u:  # Can't refer yourself
                # Save pending referral to be credited AFTER verification
                await User.saveData("pending_referral_from", ref_id, u)
        
        # Mark user as 'visited' but not 'verified' for referral purposes
        await User.saveData("is_bot_started", "true", u)

    # Use the passed not_joined list
    if not_joined:
        kb = build_force_join_keyboard(await get_all_force_join_items())
        
        caption = "<tg-emoji emoji-id=\"5296258364655805333\">🎥</tg-emoji> <b>ᴅᴏɴ'ᴛ ᴍɪꜱꜱ ᴏᴜᴛ!</b>\n\nᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟꜱ ɴᴏᴡ ᴛᴏ ᴜɴʟᴏᴄᴋ <b>ꜰʀᴇᴇ ɴᴇᴛꜰʟɪx ᴘʀᴇᴍɪᴜᴍ</b> ᴀᴄᴄᴏᴜɴᴛꜱ!\n\nᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ ʙᴇʟᴏᴡ ᴀɴᴅ ᴄʟɪᴄᴋ ᴠᴇʀɪꜰʏ <tg-emoji emoji-id=\"6111827380915934490\">✅</tg-emoji>"
        
        try:
            if config.START_MEDIA_TYPE == "photo":
                await bot.sendPhoto(chat_id=u, photo=config.START_MEDIA, caption=caption, parse_mode="html", reply_markup=kb)
            elif config.START_MEDIA_TYPE == "animation":
                await bot.sendAnimation(chat_id=u, animation=config.START_MEDIA, caption=caption, parse_mode="html", reply_markup=kb)
            elif config.START_MEDIA_TYPE == "video":
                await bot.sendVideo(chat_id=u, video=config.START_MEDIA, caption=caption, parse_mode="html", reply_markup=kb)
            else:
                await bot.sendMessage(chat_id=u, text=caption, parse_mode="html", reply_markup=kb)
        except Exception:
            await bot.sendMessage(chat_id=u, text=caption, parse_mode="html", reply_markup=kb)
        return
    

    # Main Keyboard
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="ᴍʏ ᴀᴄᴄᴏᴜɴᴛ", icon_custom_emoji_id="6035084557378654059", style="primary")
    kb.button(text="ᴡɪᴛʜᴅʀᴀᴡ ɴᴇᴛꜰʟɪx", icon_custom_emoji_id="6105053139453351459", style="success")
    kb.button(text="ʀᴇꜰᴇʀʀᴀʟ", icon_custom_emoji_id="6035033893944430595", style="primary")
    kb.button(text="ʙᴜʏ ᴄᴏɪɴs", icon_custom_emoji_id="5267300544094948794", style="success")
    kb.button(text=NETFLIX_HELP_BUTTON, icon_custom_emoji_id="6026162407066309019", style="primary")
    kb.button(text="ᴘʀᴏᴏꜰꜱ", icon_custom_emoji_id="6111827380915934490", style="primary")
    kb.adjust(2)


    welcome_text = (
        f"<tg-emoji emoji-id=\"6035033893944430595\">👋</tg-emoji> <b>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴜʟᴛɪᴍᴀᴛᴇ ɴᴇᴛꜰʟɪx ʙᴏᴛ!</b>\n\n"
        f"<tg-emoji emoji-id=\"5296258364655805333\">🎬</tg-emoji> <i>ɢᴇᴛ ᴘʀᴇᴍɪᴜᴍ ɴᴇᴛꜰʟɪx ᴀᴄᴄᴏᴜɴᴛꜱ ʙʏ ʀᴇꜰᴇʀʀɪɴɢ ꜰʀɪᴇɴᴅꜱ ᴏʀ ʀᴇᴅᴇᴇᴍɪɴɢ ᴘᴏɪɴᴛꜱ.</i>\n\n"
        f"<tg-emoji emoji-id=\"5303310030940952439\">🔥</tg-emoji> <b>ꜰᴇᴀᴛᴜʀᴇꜱ:</b>\n"
        f"• ɪɴꜱᴛᴀɴᴛ ᴅᴇʟɪᴠᴇʀʏ\n"
        f"• ʀᴇꜰᴇʀʀᴀʟ ʀᴇᴡᴀʀᴅꜱ\n"
        f"• 24/7 ꜱᴜᴘᴘᴏʀᴛ\n\n"
        f"<tg-emoji emoji-id=\"6201809243574638159\">👇</tg-emoji> <b>ᴜꜱᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ ᴛᴏ ɴᴀᴠɪɢᴀᴛᴇ.</b>"
    )
    
    try:
        if config.START_MEDIA_TYPE == "photo":
            await bot.sendPhoto(chat_id=u, photo=config.START_MEDIA, caption=welcome_text, parse_mode="html", reply_markup=kb.as_markup(resize_keyboard=True, input_field_placeholder="🍿 Choose a Netflix plan below..."))
        elif config.START_MEDIA_TYPE == "animation":
            await bot.sendAnimation(chat_id=u, animation=config.START_MEDIA, caption=welcome_text, parse_mode="html", reply_markup=kb.as_markup(resize_keyboard=True, input_field_placeholder="🍿 Choose a Netflix plan below..."))
        elif config.START_MEDIA_TYPE == "video":
            await bot.sendVideo(chat_id=u, video=config.START_MEDIA, caption=welcome_text, parse_mode="html", reply_markup=kb.as_markup(resize_keyboard=True, input_field_placeholder="🍿 Choose a Netflix plan below..."))
        else:
            await bot.sendMessage(chat_id=u, text=welcome_text, parse_mode="html", reply_markup=kb.as_markup(resize_keyboard=True, input_field_placeholder="🍿 Choose a Netflix plan below..."))
    except Exception:
        await bot.sendMessage(chat_id=u, text=welcome_text, parse_mode="html", reply_markup=kb.as_markup(resize_keyboard=True, input_field_placeholder="🍿 Choose a Netflix plan below..."))
    

@router.callback_query(F.data == "verify_join")
async def cb_verify_join(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    not_joined = []
    for item in await get_all_force_join_items():
        channel = item["chat_id"]
        try:
            member = await callback.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(item)
        except Exception:
            not_joined.append(item)

    if not_joined:
        await callback.answer("⚠️ ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴄᴀᴀɴɴᴇʟ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ ʏᴇᴛ!", show_alert=True)
    else:
        await callback.answer("✅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ!", show_alert=True)
        try:
            await callback.message.delete()
        except:
            pass
        # Build fresh start menu directly (fixing main menu not opening bug)
        u = callback.from_user.id
        from utils.bdft_env import BDFTBot, BDFTUser, BDFTLibs
        bot = BDFTBot(callback.bot)
        User = BDFTUser()

        from aiogram.utils.keyboard import ReplyKeyboardBuilder
        kb2 = ReplyKeyboardBuilder()
        kb2.button(text="ᴍʏ ᴀᴄᴄᴏᴜɴᴛ", icon_custom_emoji_id="6035084557378654059")
        kb2.button(text="ᴡɪᴛʜᴅʀᴀᴡ ɴᴇᴛꜰʟɪx", icon_custom_emoji_id="6105053139453351459")
        kb2.button(text="ʀᴇꜰᴇʀʀᴀʟ", icon_custom_emoji_id="6035033893944430595")
        kb2.button(text="ʙᴜʏ ᴄᴏɪɴs", icon_custom_emoji_id="5267300544094948794")
        kb2.button(text=NETFLIX_HELP_BUTTON, icon_custom_emoji_id="6026162407066309019")
        kb2.button(text="ᴘʀᴏᴏꜰꜱ", icon_custom_emoji_id="6111827380915934490")
        kb2.adjust(2)

        welcome_text = (
            f"<tg-emoji emoji-id=\"6111827380915934490\">✅</tg-emoji> <b>ʏᴏᴜ'ʀᴇ ᴠᴇʀɪꜰɪᴇᴅ, {callback.from_user.first_name}!</b>\n\n"
            f"<tg-emoji emoji-id=\"5296258364655805333\">🎬</tg-emoji> <i>ɢᴇᴛ ᴘʀᴇᴍɪᴜᴍ ɴᴇᴛꜰʟɪx ᴀᴄᴄᴏᴜɴᴛꜱ ʙʏ ʀᴇꜰᴇʀʀɪɴɢ ꜰʀɪᴇɴᴅꜱ ᴏʀ ʀᴇᴅᴇᴇᴍɪɴɢ ᴘᴏɪɴᴛꜱ!</i>\n\n"
            f"<tg-emoji emoji-id=\"5303310030940952439\">🔥</tg-emoji> <b>ꜰᴇᴀᴛᴜʀᴇꜱ:</b>\n"
            f"• ɪɴꜱᴛᴀɴᴛ ᴅᴇʟɪᴠᴇʀʏ\n"
            f"• ʀᴇꜰᴇʀʀᴀʟ ʀᴇᴡᴀʀᴅꜱ\n"
            f"• 24/7 ꜱᴜᴘᴘᴏʀᴛ\n\n"
            f"<tg-emoji emoji-id=\"6201809243574638159\">👇</tg-emoji> <b>ᴜꜱᴇ ᴛʜᴇ ᴁᴜᴛᴛᴏɴꜱ ᴁᴇʟᴏᴡ ᴛᴏ ɴᴀᴠɪɢᴀᴛᴇ.</b>"
        )

        if config.START_MEDIA_TYPE == "photo":
            await bot.sendPhoto(chat_id=u, photo=config.START_MEDIA, caption=welcome_text, parse_mode="html", reply_markup=kb2.as_markup(resize_keyboard=True, input_field_placeholder="🍿 Choose a Netflix plan below..."))
        elif config.START_MEDIA_TYPE == "animation":
            await bot.sendAnimation(chat_id=u, animation=config.START_MEDIA, caption=welcome_text, parse_mode="html", reply_markup=kb2.as_markup(resize_keyboard=True, input_field_placeholder="🍿 Choose a Netflix plan below..."))
        elif config.START_MEDIA_TYPE == "video":
            await bot.sendVideo(chat_id=u, video=config.START_MEDIA, caption=welcome_text, parse_mode="html", reply_markup=kb2.as_markup(resize_keyboard=True, input_field_placeholder="🍿 Choose a Netflix plan below..."))
        else:
            await bot.sendMessage(chat_id=u, text=welcome_text, parse_mode="html", reply_markup=kb2.as_markup(resize_keyboard=True, input_field_placeholder="🍿 Choose a Netflix plan below..."))

        # --- Referral Crediting (Apply Points After Successful Verification) ---
        is_referral_done = await User.getData("is_started", user_id)
        if not is_referral_done:
            # Mark as completely started/verified
            await User.saveData("is_started", "true", user_id)
            
            ref_id = await User.getData("pending_referral_from", user_id)
            if ref_id:
                try:
                    # 1. Update Referrer Balance
                    ref_bal = await User.getData("balance", ref_id) or 0
                    await User.saveData("balance", int(ref_bal) + 1, ref_id)
                    
                    # 2. Update Referrer Count
                    all_ref_counts = await bot.getData("ref_counts") or {}
                    ref_id_str = str(ref_id)
                    current_count = all_ref_counts.get(ref_id_str, 0)
                    all_ref_counts[ref_id_str] = int(current_count) + 1
                    await bot.saveData("ref_counts", all_ref_counts)
                    
                    # 3. Notify Referrer
                    notif_msg = (
                        f"<tg-emoji emoji-id=\"6026162407066309019\">🎉</tg-emoji> <b>ɴᴇᴡ ᴠᴇʀɪꜰɪᴇᴅ ʀᴇꜰᴇʀʀᴀʟ!</b>\n\n"
                        f"<tg-emoji emoji-id=\"6111827380915934490\">✅</tg-emoji> ᴀ ᴜꜱᴇʀ ᴊᴏɪɴᴇᴅ ᴀɴᴅ ᴠᴇʀɪꜰɪᴇᴅ!\n"
                        f"<tg-emoji emoji-id=\"5350452584119279096\">💰</tg-emoji> ʏᴏᴜ'ᴠᴇ ᴇᴀʀɴᴇᴅ <b>1 ᴘᴏɪɴᴛ</b>.\n"
                        f"<tg-emoji emoji-id=\"6035084557378654059\">👤</tg-emoji> ᴛᴏᴛᴀʟ ᴠᴇʀɪꜰɪᴇᴅ ʀᴇꜰᴇʀʀᴀʟꜱ: <b>{int(current_count) + 1}</b>"
                    )
                    await callback.bot.send_message(ref_id, notif_msg, parse_mode="html")
                    
                    # Clear pending status
                    await User.saveData("pending_referral_from", None, user_id)
                except Exception as e:
                    print(f"Referral Credit Error: {e}")

@router.message(F.text == "ᴍʏ ᴀᴄᴄᴏᴜɴᴛ")
async def cmd_my_account(message: types.Message):
    env = await get_env(message)
    u, bot, Bot, User, message = env['u'], env['bot'], env['Bot'], env['User'], env['message']
    
    pic6 = "https://ibb.co/Tqks39Qg"
    balance = await User.getData("balance", u) or 0
    now = BDFTLibs.dateandtime.now("Asia/kolkata")
    
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start={u}"
    
    caption = (
        f"<b>• ━━━━━━━━━━━━━ •</b>\n"
        f"<tg-emoji emoji-id=\"6035084557378654059\">👤</tg-emoji> ɴᴀᴍᴇ: <code>{message.from_user.first_name}</code>\n"
        f"<tg-emoji emoji-id=\"6201809243574638159\">🆔</tg-emoji> ᴜꜱᴇʀ ɪᴅ: <code>{u}</code>\n"
        f"<tg-emoji emoji-id=\"5350452584119279096\">💰</tg-emoji> ʙᴀʟᴀɴᴄᴇ: <code>{balance} ᴘᴏɪɴᴛꜱ</code>\n\n"
        f"<tg-emoji emoji-id=\"5451732530048802485\">⏳</tg-emoji> ᴛɪᴍᴇ: <code>{now['time']}</code>\n"
        f"<tg-emoji emoji-id=\"5800810214689084012\">📅</tg-emoji> ᴅᴀᴛᴇ: <code>{now['date']}</code>\n\n"
        f"<tg-emoji emoji-id=\"5782841896883721810\">🎁</tg-emoji> <b>ꜱʜᴀʀᴇ & ᴇᴀʀɴ:</b> ɢᴇᴛ ɴᴇᴛꜰʟɪx ᴘʀᴇᴍɪᴜᴍ ꜰʀᴇᴇ!\n"
        f"3 ᴘᴏɪɴᴛꜱ = 1 ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴏᴜɴᴛ\n\n"
        f"<tg-emoji emoji-id=\"6026162407066309019\">💡</tg-emoji> ᴛɪᴘ: ꜱʜᴀʀᴇ ʏᴏᴜʀ ʀᴇꜰᴇʀʀᴀʟ ʟɪɴᴋ ᴛᴏ ᴇᴀʀɴ ᴘᴏɪɴᴛꜱ!\n"
        f"<b>• ━━━━━━━━━━━━━ •</b>"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="ꜱʜᴀʀᴇ ʀᴇꜰᴇʀʀᴀʟ ʟɪɴᴋ", url=f"https://t.me/share/url?url={ref_link}&text=Get%20Netflix%20Premium%20FREE!", icon_custom_emoji_id="5080213825970505261", style="success"))
    
    await bot.sendPhoto(chat_id=u, photo=pic6, caption=caption, parse_mode="html", reply_markup=kb.as_markup())

@router.message(F.text == "ᴘʀᴏᴏꜰꜱ")
async def cmd_proofs(message: types.Message):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb_proof = InlineKeyboardBuilder()
    kb_proof.add(InlineKeyboardButton(text="ᴠɪᴇᴡ ᴘʀᴏᴏꜰꜱ ᴄʜᴀɴɴᴇʟ", url="https://t.me/ProofLogsChannel", style="primary", icon_custom_emoji_id="5780405967527089720"))
    await message.answer("<tg-emoji emoji-id=\"6111827380915934490\">✅</tg-emoji> <b>ᴄʜᴇᴄᴋ ᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ & ᴅᴇʟɪᴠᴇʀʏ ᴘʀᴏᴏꜰꜱ ʜᴇʀᴇ:</b>", parse_mode="html", reply_markup=kb_proof.as_markup())

@router.message(Command("nftokenhelp"))
@router.message(F.text == NETFLIX_HELP_BUTTON)
async def cmd_netflix_help(message: types.Message):
    await message.answer(NETFLIX_HELP_TEXT, parse_mode="html")

@router.message(F.text == "ᴡɪᴛʜᴅʀᴀᴡ ɴᴇᴛꜰʟɪx")
async def cmd_withdraw_netflix(message: types.Message):
    # This just redirects to the services handler
    from handlers.services import cmd_netflix
    await cmd_netflix(message)

@router.message(F.text == "ʀᴇꜰᴇʀʀᴀʟ")
async def cmd_referral(message: types.Message):
    env = await get_env(message)
    u, bot, Bot, User, message = env['u'], env['bot'], env['Bot'], env['User'], env['message']
    
    all_ref_counts = await Bot.getData("ref_counts") or {}
    total_refer = all_ref_counts.get(str(u), 0)
    
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    link = f"https://t.me/{bot_username}?start={u}"
    
    msg = (
        f"<tg-emoji emoji-id=\"6026162407066309019\">✨</tg-emoji> <b>ɴᴇᴛꜰʟɪx ᴘʀᴇᴍɪᴜᴍ ɢᴇɴᴇʀᴀᴛᴏʀ</b> <tg-emoji emoji-id=\"6026162407066309019\">✨</tg-emoji>\n\n"
        f"<tg-emoji emoji-id=\"5296258364655805333\">🎬</tg-emoji> ᴜɴʟᴏᴄᴋ ꜰʀᴇᴇ ɴᴇᴛꜰʟɪx ᴘʀᴇᴍɪᴜᴍ ʙʏ ʀᴇꜰᴇʀʀɪɴɢ ꜰʀɪᴇɴᴅꜱ!\n"
        f"<tg-emoji emoji-id=\"5303310030940952439\">🔥</tg-emoji> ɪɴꜱᴛᴀɴᴛ ᴀᴄᴄᴇꜱꜱ & ꜱᴇᴄᴜʀᴇ.\n\n"
        f"<tg-emoji emoji-id=\"6035033893944430595\">👥</tg-emoji> ɪɴᴠɪᴛᴇ ꜰʀɪᴇɴᴅꜱ & ᴇᴀʀɴ ᴘᴏɪɴᴛꜱ.\n"
        f"<tg-emoji emoji-id=\"5350452584119279096\">💎</tg-emoji> ᴍᴏʀᴇ ʀᴇꜰᴇʀʀᴀʟꜱ = ᴍᴏʀᴇ ɴᴇᴛꜰʟɪx ᴀᴄᴄᴏᴜɴᴛꜱ.\n\n"
        f"<tg-emoji emoji-id=\"5780405967527089720\">🔗</tg-emoji> ʏᴏᴜʀ ʀᴇꜰᴇʀʀᴀʟ ʟɪɴᴋ:\n"
        f"<code>{link}</code>\n\n"
        f"<tg-emoji emoji-id=\"6035084557378654059\">👤</tg-emoji> ᴛᴏᴛᴀʟ ʀᴇꜰᴇʀʀᴀʟꜱ: <code>{total_refer}</code> ᴜꜱᴇʀꜱ"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="ꜱʜᴀʀᴇ ʀᴇꜰᴇʀʀᴀʟ ʟɪɴᴋ", url=f"https://t.me/share/url?url={link}&text=Get%20Netflix%20Premium%20FREE!", icon_custom_emoji_id="5080213825970505261", style="success"))
    
    await bot.sendPhoto(
        chat_id=u,
        photo="https://ibb.co/ymvsRj3m",
        caption=msg,
        parse_mode="html",
        reply_markup=kb.as_markup()
    )
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    ...
# --- User Settings (Email & Wallet) ---

@router.message(Command("setemail"))
async def cmd_set_email(message: types.Message, state: FSMContext):
    await message.answer("📧 <b>Please enter the Email Address where you want to receive your account details.</b>\n\nTo cancel, type /cancel", parse_mode="html")
    await state.set_state(UserSettingsStates.waiting_for_email)

@router.message(UserSettingsStates.waiting_for_email)
async def process_set_email(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Email setting cancelled.")
        return

    email = message.text.strip()
    if "@" not in email or "." not in email:
        await message.answer("❌ Invalid Email Format! Please enter a valid email address.")
        return

    await db.save_user_data(message.from_user.id, "email", email)
    await state.clear()
    await message.answer(f"✅ <b>Success!</b> Your email address (<code>{email}</code>) has been saved.", parse_mode="html")

@router.message(Command("setwallet"))
async def cmd_set_wallet(message: types.Message, state: FSMContext):
    await message.answer("🏦 <b>Please enter your Wallet Address (e.g. Binance ID or UPI).</b>\n\nTo cancel, type /cancel", parse_mode="html")
    await state.set_state(UserSettingsStates.waiting_for_wallet)

@router.message(UserSettingsStates.waiting_for_wallet)
async def process_set_wallet(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Wallet setting cancelled.")
        return

    wallet = message.text.strip()
    await db.save_user_data(message.from_user.id, "wallet", wallet)
    await state.clear()
    await message.answer(f"✅ <b>Success!</b> Your wallet address (<code>{wallet}</code>) has been saved.", parse_mode="html")
