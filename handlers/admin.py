import asyncio
import html
from datetime import datetime, timezone
from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.bdft_env import BDFTBot, BDFTUser, BDFTLibs
from utils.db_manager import db
from utils.force_join import (
    get_all_force_join_items,
    get_extra_force_join_items,
    normalize_button_url,
    normalize_private_channel,
    normalize_public_channel,
    render_channel_list,
    save_extra_force_join_items,
)
from config import config
import re

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

class AdminStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_stock = State()
    waiting_for_broadcast = State()
    waiting_for_public_channel_add = State()
    waiting_for_public_channel_link = State()
    waiting_for_private_channel_add = State()
    waiting_for_channel_remove = State()


def build_channels_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Public Channel Add", callback_data="fj:add_public")
    kb.button(text="Private Force Add", callback_data="fj:add_private")
    kb.button(text="Remove Extra", callback_data="fj:remove")
    kb.button(text="View All", callback_data="fj:list")
    kb.button(text="Clear Extra", callback_data="fj:clear")
    kb.button(text="Back", callback_data="fj:back")
    kb.adjust(2, 2, 2)
    return kb.as_markup()


def build_admin_keyboard():
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ", icon_custom_emoji_id="6258267877170745815")
    kb.button(text="ʙʀᴏᴀᴅᴄᴀꜱᴛ", icon_custom_emoji_id="5780405967527089720")
    kb.button(text="ᴍᴀɴᴀɢᴇ ᴄᴏɪɴꜱ", icon_custom_emoji_id="5350452584119279096")
    kb.button(text="ɢᴇɴ ᴄᴏᴜᴘᴏɴ", icon_custom_emoji_id="5377624166436445368")
    kb.button(text="ᴀᴅᴅ ꜱᴛᴏᴄᴋ", icon_custom_emoji_id="5431492767249342908")
    kb.button(text="ᴘᴜꜱʜ ɢɪᴛʜᴜʙ", icon_custom_emoji_id="5780167709393832926")
    kb.button(text="manage channels", icon_custom_emoji_id="6260243270069130135")
    kb.button(text="ᴄʜᴇᴄᴋ ꜱᴛᴏᴄᴋ", icon_custom_emoji_id="5303310030940952439")
    kb.button(text="ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", icon_custom_emoji_id="5312486108309757006")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


async def send_admin_panel(message: types.Message):
    await message.answer(
        "<tg-emoji emoji-id=\"6113753759647539172\">👑</tg-emoji> <b>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ</b>\n\nꜱᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʙᴇʟᴏᴡ.",
        parse_mode="html",
        reply_markup=build_admin_keyboard(),
    )

async def get_env(message: types.Message):
    return {
        "u": message.from_user.id,
        "bot": BDFTBot(message.bot),
        "Bot": BDFTBot(message.bot),
        "User": BDFTUser(),
        "message": message
    }


def guarantee_status(order: dict) -> str:
    expires_at = datetime.fromisoformat(order["guarantee_expires_at"])
    return "ACTIVE" if expires_at >= datetime.now(timezone.utc) else "EXPIRED"

@router.message(Command("admin"))
@router.message(Command("panel"))
async def cmd_admin_panel(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return

    await send_admin_panel(message)

@router.message(F.text == "manage channels")
async def admin_manage_channels(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return
    channels = await get_all_force_join_items()
    await message.answer(
        render_channel_list(channels),
        parse_mode="html",
        reply_markup=build_channels_menu(),
    )


@router.callback_query(F.data == "fj:back")
async def cb_force_join_back(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_admin_panel(callback.message)


@router.callback_query(F.data == "fj:list")
async def cb_force_join_list(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return
    channels = await get_all_force_join_items()
    await callback.answer("Channels refreshed", show_alert=False)
    try:
        await callback.message.edit_text(
            render_channel_list(channels),
            parse_mode="html",
            reply_markup=build_channels_menu(),
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


@router.callback_query(F.data == "fj:clear")
async def cb_force_join_clear(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return
    await save_extra_force_join_items([])
    channels = await get_all_force_join_items()
    await callback.answer("Extra channels cleared. Default channels kept.", show_alert=True)
    await callback.message.edit_text(
        render_channel_list(channels),
        parse_mode="html",
        reply_markup=build_channels_menu(),
    )


@router.callback_query(F.data == "fj:add_public")
async def cb_force_join_add_public(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        return
    await state.set_state(AdminStates.waiting_for_public_channel_add)
    await callback.answer()
    await callback.message.answer(
        "<b>Step 1: send public channel username for membership check.</b>\n\n"
        "Examples:\n"
        "<code>@MyChannel</code>\n"
        "<code>https://t.me/MyChannel</code>\n"
        "\nNext step will ask the invite/button link separately.\n"
        "Type /cancel to stop.",
        parse_mode="html",
    )


@router.callback_query(F.data == "fj:add_private")
async def cb_force_join_add_private(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        return
    await state.set_state(AdminStates.waiting_for_private_channel_add)
    await callback.answer()
    await callback.message.answer(
        "<b>Send private channel chat id and invite link.</b>\n\n"
        "Format:\n"
        "<code>-1001234567890 | https://t.me/+InviteCode</code>\n\n"
        "The bot must be admin/member in that private channel so it can check users.\n"
        "Type /cancel to stop.",
        parse_mode="html",
    )


@router.callback_query(F.data == "fj:remove")
async def cb_force_join_remove(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        return
    await state.set_state(AdminStates.waiting_for_channel_remove)
    await callback.answer()
    await callback.message.answer(
        "<b>Send extra channel username or private chat id to remove.</b>\n\n"
        "Examples:\n"
        "<code>@MyChannel</code>\n"
        "<code>-1001234567890</code>\n\n"
        "Default channels are kept safe and cannot be removed here.\n"
        "Type /cancel to stop.",
        parse_mode="html",
    )


@router.message(AdminStates.waiting_for_public_channel_add)
async def process_force_join_public_add(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        await state.clear()
        return
    if (message.text or "").strip() == "/cancel":
        await state.clear()
        await message.answer("Cancelled.")
        return

    item = normalize_public_channel(message.text)
    if item is None:
        await message.answer("<b>Invalid public channel. Send @username or public t.me link.</b>", parse_mode="html")
        return

    extras = await get_extra_force_join_items()
    all_items = await get_all_force_join_items()
    if any(existing["chat_id"] == item["chat_id"] for existing in all_items):
        await state.clear()
        await message.answer("<b>That channel is already in the list.</b>", parse_mode="html")
        return

    await state.update_data(public_channel_item=item)
    await state.set_state(AdminStates.waiting_for_public_channel_link)
    await message.answer(
        "<b>Step 2: send the invite/link for the button.</b>\n\n"
        "Examples:\n"
        "<code>https://t.me/MyChannel</code>\n"
        "<code>https://t.me/+InviteCode</code>\n\n"
        "This link is only for the button. Membership check will use the username from step 1.\n"
        "Type /cancel to stop.",
        parse_mode="html",
    )


@router.message(AdminStates.waiting_for_public_channel_link)
async def process_force_join_public_link(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        await state.clear()
        return
    if (message.text or "").strip() == "/cancel":
        await state.clear()
        await message.answer("Cancelled.")
        return

    button_url = normalize_button_url(message.text)
    if button_url is None:
        await message.answer("<b>Invalid button link. Send a t.me link or @username.</b>", parse_mode="html")
        return

    data = await state.get_data()
    item = data.get("public_channel_item")
    if not item:
        await state.clear()
        await message.answer("<b>Public channel step expired. Start again.</b>", parse_mode="html")
        return

    extras = await get_extra_force_join_items()
    all_items = await get_all_force_join_items()
    if any(existing["chat_id"] == item["chat_id"] for existing in all_items):
        await state.clear()
        await message.answer("<b>That channel is already in the list.</b>", parse_mode="html")
        return

    item["url"] = button_url
    extras.append(item)
    await save_extra_force_join_items(extras)
    await state.clear()
    await message.answer(
        f"<b>Public channel added:</b> <code>{html.escape(str(item['chat_id']))}</code>\n"
        f"<b>Button link:</b> <code>{html.escape(button_url)}</code>",
        parse_mode="html",
        reply_markup=build_channels_menu(),
    )


@router.message(AdminStates.waiting_for_private_channel_add)
async def process_force_join_private_add(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        await state.clear()
        return
    if (message.text or "").strip() == "/cancel":
        await state.clear()
        await message.answer("Cancelled.")
        return

    item = normalize_private_channel(message.text)
    if item is None:
        await message.answer(
            "<b>Invalid private channel format.</b>\nUse:\n<code>-1001234567890 | https://t.me/+InviteCode</code>",
            parse_mode="html",
        )
        return

    extras = await get_extra_force_join_items()
    all_items = await get_all_force_join_items()
    if any(existing["chat_id"] == item["chat_id"] for existing in all_items):
        await state.clear()
        await message.answer("<b>That private channel is already in the list.</b>", parse_mode="html")
        return

    extras.append(item)
    await save_extra_force_join_items(extras)
    await state.clear()
    await message.answer(
        f"<b>Private force channel added:</b> <code>{html.escape(str(item['chat_id']))}</code>",
        parse_mode="html",
        reply_markup=build_channels_menu(),
    )


@router.message(AdminStates.waiting_for_channel_remove)
async def process_force_join_remove(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        await state.clear()
        return
    if (message.text or "").strip() == "/cancel":
        await state.clear()
        await message.answer("Cancelled.")
        return

    raw = (message.text or "").strip()
    public_item = normalize_public_channel(raw)
    if public_item:
        chat_id = public_item["chat_id"]
    elif raw.lstrip("-").isdigit():
        chat_id = int(raw)
    else:
        await message.answer("<b>Invalid channel reference.</b>", parse_mode="html")
        return

    extras = await get_extra_force_join_items()
    if not any(item["chat_id"] == chat_id for item in extras):
        await state.clear()
        await message.answer("<b>That extra channel was not found.</b>", parse_mode="html")
        return

    extras = [item for item in extras if item["chat_id"] != chat_id]
    await save_extra_force_join_items(extras)
    await state.clear()
    await message.answer(
        f"<b>Removed extra channel:</b> <code>{html.escape(str(chat_id))}</code>",
        parse_mode="html",
        reply_markup=build_channels_menu(),
    )


@router.message(Command("setbalance"))
async def cmd_set_balance(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return

    env = await get_env(message)
    bot, User = env['bot'], env['User']

    # Format: /setbalance 123456789 50
    args = message.text.split()
    if len(args) != 3:
        await bot.sendMessage(message.chat.id, "⚠️ Format Error! Use:\n`/setbalance USER_ID AMOUNT`", parse_mode="html")
        return

    target_uid = args[1]
    if not target_uid.isdigit():
        await bot.sendMessage(message.chat.id, "❌ USER_ID must be numeric.")
        return

    try:
        amount = int(args[2])
        # Save to user collection directly
        await User.saveData("balance", amount, target_uid)
        
        # User notification
        try:
            await bot.sendMessage(target_uid, f"<b>🎉 Admin has set your balance to {amount} Points!</b>", parse_mode="html")
        except:
            pass
            
        await bot.sendMessage(message.chat.id, f"✅ User <code>{target_uid}</code> balance set to <b>{amount}</b>.", parse_mode="html")
    except ValueError:
        await bot.sendMessage(message.chat.id, "❌ AMOUNT must be a number.")

@router.message(Command("gcheck"))
async def cmd_guarantee_check(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return

    from handlers.services import CLAIM_CONTACT, format_display_dt

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "<b>Usage:</b>\n<code>/gcheck USER_ID</code>",
            parse_mode="html",
        )
        return

    target_user_id = int(parts[1])
    orders = await db.get_netflix_guarantee_orders(target_user_id, limit=10)
    if not orders:
        await message.answer(
            f"<b>No guarantee records found for</b> <code>{target_user_id}</code>.",
            parse_mode="html",
        )
        return

    lines = [
        "<b>Guarantee Check</b>",
        f"User: <code>{target_user_id}</code>",
        f"Claim: <b>{CLAIM_CONTACT}</b>",
        "",
    ]

    for order in orders:
        lines.extend([
            f"<b>{order['product_type']}</b>",
            f"• order id: <code>{order['order_id']}</code>",
            f"• delivered: <code>{format_display_dt(order['delivered_at'])}</code>",
            f"• expires: <code>{format_display_dt(order['guarantee_expires_at'])}</code>",
            f"• status: <b>{guarantee_status(order)}</b>",
            "",
        ])

    await message.answer("\n".join(lines).rstrip(), parse_mode="html")


@router.message(Command("stats"))
@router.message(F.text == "ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ")
async def cmd_stats(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return
    all_users = await db.get_all_users()
    total_users = len(all_users)
    
    # We can add more stats like total accounts in stock later
    total_stock = await db.get_bot_data("NF", 0)
    
    stats_text = (
        f"<tg-emoji emoji-id=\"6258267877170745815\">📊</tg-emoji> <b>ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ</b>\n\n"
        f"<tg-emoji emoji-id=\"6035033893944430595\">👥</tg-emoji> ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ: <code>{total_users}</code>\n"
        f"<tg-emoji emoji-id=\"5431492767249342908\">📦</tg-emoji> ᴛᴏᴛᴀʟ ɴᴇᴛꜰʟɪx ꜱᴛᴏᴄᴋ: <code>{total_stock}</code>\n"
        f"<tg-emoji emoji-id=\"5296258364655805333\">🎬</tg-emoji> ꜰᴏᴄᴜꜱ: <b>ɴᴇᴛꜰʟɪx ᴏɴʟʏ</b>"
    )
    
    await message.answer(stats_text, parse_mode="html")

@router.message(F.text == "ᴍᴀɴᴀɢᴇ ᴄᴏɪɴꜱ")
@router.message(F.text == "ᴍᴀɴᴀɢᴇ ʙᴀʟᴀɴᴄᴇ")
async def admin_manage_balance(message: types.Message):
    if message.from_user.id not in config.ADMINS: return
    await message.answer(
        "<tg-emoji emoji-id=\"5350452584119279096\">💰</tg-emoji> <b>ᴍᴀɴᴀɢᴇ ʙᴀʟᴀɴᴄᴇ</b>\n\n"
        "<b>ᴜꜱᴀɢᴇ:</b>\n"
        "<code>/setbalance USER_ID AMOUNT</code>\n\n"
        "<b>ᴇxᴀᴍᴘʟᴇ:</b>\n"
        "<code>/setbalance 123456789 10</code>",
        parse_mode="html"
    )

@router.message(F.text == "ɢᴇɴ ᴄᴏᴜᴘᴏɴ")
async def admin_gen_coupon_info(message: types.Message):
    if message.from_user.id not in config.ADMINS: return
    await message.answer(
        "<tg-emoji emoji-id=\"5377624166436445368\">🎟</tg-emoji> <b>ɢᴇɴᴇʀᴀᴛᴇ ᴄᴏᴜᴘᴏɴ</b>\n\n"
        "<b>ᴜꜱᴀɢᴇ:</b>\n"
        "<code>/gen_coupon AMOUNT</code>\n\n"
        "<b>ᴇxᴀᴍᴘʟᴇ:</b>\n"
        "<code>/gen_coupon 5</code>\n"
        "<i>This generates a coupon worth 5 points.</i>",
        parse_mode="html"
    )

@router.message(F.text == "ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ")
async def admin_back_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔙 ʀᴇᴛᴜʀɴɪɴɢ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ...", reply_markup=types.ReplyKeyboardRemove())
    from handlers.user import cmd_start
    await cmd_start(message, not_joined=[])

# --- Add Stock Button Handler ---
@router.message(F.text == "ᴀᴅᴅ ꜱᴛᴏᴄᴋ")
async def admin_add_stock_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS: return
    await state.set_state(AdminStates.waiting_for_stock)
    await message.answer(
        "<tg-emoji emoji-id=\"5431492767249342908\">📦</tg-emoji> <b>ᴀᴅᴅ ɴᴇᴛꜰʟɪx ꜱᴛᴏᴄᴋ</b>\n\n"
        "<b>ꜰᴏʀᴍᴀᴛ:</b>\n"
        "<code>email1@gmail.com:password1\n"
        "email2@gmail.com:password2\n"
        "email3@gmail.com:password3</code>\n\n"
        "<i>Each line = 1 Account. Send multiple at once!</i>\n"
        "Type /cancel to abort.",
        parse_mode="html"
    )

@router.message(AdminStates.waiting_for_stock)
async def admin_add_stock_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        await state.clear()
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ <b>Cancelled.</b>", parse_mode="html")
        return

    env = await get_env(message)
    Bot = env['Bot']

    lines = message.text.strip().split("\n")
    added = 0
    current_nf = await Bot.getData("NF") or 0
    current_nf = int(current_nf)

    for line in lines:
        line = line.strip()
        if ":" in line:
            email, password = line.split(":", 1)
            current_nf += 1
            account_data = {"Email": email.strip(), "Pass": password.strip()}
            await Bot.saveData(f"NFAcc{current_nf}", account_data)
            added += 1

    await state.clear()
    if added > 0:
        await Bot.saveData("NF", current_nf)
        await message.answer(
            f"<tg-emoji emoji-id=\"6111827380915934490\">✅</tg-emoji> <b>ꜱᴜᴄᴄᴇꜱꜱ!</b>\n\n"
            f"<tg-emoji emoji-id=\"5431492767249342908\">📦</tg-emoji> <b>{added} ɴᴇᴛꜰʟɪx ᴀᴄᴄᴏᴜɴᴛꜱ ᴀᴅᴅᴇᴅ!</b>\n"
            f"ᴛᴏᴛᴀʟ ꜱᴛᴏᴄᴋ ɴᴏᴡ: <code>{current_nf}</code>",
            parse_mode="html"
        )
    else:
        await message.answer(
            "<tg-emoji emoji-id=\"5765005318610228026\">❌</tg-emoji> <b>No valid accounts found!</b>\n\n"
            "Make sure format is:\n<code>email@gmail.com:password</code>",
            parse_mode="html"
        )

# --- Check / Push Stock Button ---
@router.message(F.text == "ᴄʜᴇᴄᴋ ꜱᴛᴏᴄᴋ")
async def admin_check_stock(message: types.Message):
    if message.from_user.id not in config.ADMINS: return
    env = await get_env(message)
    Bot = env['Bot']
    current_nf = await Bot.getData("NF") or 0
    dispensed = await Bot.getData("Apma") or 0
    remaining = int(current_nf) - int(dispensed)
    await message.answer(
        f"<tg-emoji emoji-id=\"5431492767249342908\">📦</tg-emoji> <b>ꜱᴛᴏᴄᴋ ꜱᴛᴀᴛᴜꜱ</b>\n\n"
        f"ᴛᴏᴛᴀʟ ᴀᴅᴅᴇᴅ: <code>{current_nf}</code>\n"
        f"ᴅᴇʟɪᴠᴇʀᴇᴅ: <code>{dispensed}</code>\n"
        f"ʀᴇᴍᴀɪɴɪɴɢ: <b>{remaining}</b>",
        parse_mode="html"
    )

# --- Push Github Button ---
@router.message(F.text == "ᴘᴜꜱʜ ɢɪᴛʜᴜʙ")
async def admin_push_github(message: types.Message):
    if message.from_user.id not in config.ADMINS: return
    await message.answer("<i>⚙️ GitHub push is handled manually via terminal.</i>", parse_mode="html")



@router.message(Command("pinall"))
async def admin_pinall(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return
    if not message.reply_to_message:
        await message.answer("📌 <b>Usage:</b> Reply to any message with <code>/pinall</code>", parse_mode="html")
        return

    users = await db.get_all_users()
    status_msg = await message.answer(f"📌 <b>Pinning replied message for {len(users)} users...</b>", parse_mode="html")
    sent = pinned = failed = 0
    for user_id in users:
        try:
            copied = await message.bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id,
            )
            sent += 1
            await message.bot.pin_chat_message(
                chat_id=user_id,
                message_id=copied.message_id,
                disable_notification=True,
            )
            pinned += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await status_msg.edit_text(
        f"✅ <b>Pin All Complete</b>\nSent: <code>{sent}/{len(users)}</code>\nPinned: <code>{pinned}/{len(users)}</code>\nFailed: <code>{failed}</code>",
        parse_mode="html",
    )


@router.message(Command("unpinall"))
async def admin_unpinall(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return
    users = await db.get_all_users()
    status_msg = await message.answer(f"📍 <b>Unpinning latest pinned message for {len(users)} users...</b>", parse_mode="html")
    done = failed = 0
    for user_id in users:
        try:
            await message.bot.unpin_chat_message(chat_id=user_id)
            done += 1
            await asyncio.sleep(0.03)
        except Exception:
            failed += 1
    await status_msg.edit_text(
        f"✅ <b>Unpin All Complete</b>\nDone: <code>{done}/{len(users)}</code>\nFailed: <code>{failed}</code>",
        parse_mode="html",
    )

# --- Broadcast Handlers ---
@router.message(F.text == "ʙʀᴏᴀᴅᴄᴀꜱᴛ")
async def admin_broadcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS: return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await message.answer(
        "<tg-emoji emoji-id=\"5780405967527089720\">📢</tg-emoji> <b>ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴍᴇꜱꜱᴀɢᴇ</b>\n\n"
        "ꜱᴇɴᴅ ᴛʜᴇ ᴍᴇꜱꜱᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀꜱ.\n"
        "ɪᴛ ᴄᴀɴ ʙᴇ ᴛᴇxᴛ, ᴘʜᴏᴛᴏ, ᴏʀ ᴀɴɪᴍᴀᴛɪᴏɴ.\n\n"
        "Type /cancel to abort.",
        parse_mode="html"
    )

@router.message(AdminStates.waiting_for_broadcast)
async def admin_broadcast_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        await state.clear()
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ <b>Broadcast cancelled.</b>", parse_mode="html")
        return

    await state.clear()
    users = await db.get_all_users()
    count = 0
    await message.answer(f"⏳ <b>ꜱᴛᴀʀᴛɪɴɢ ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴛᴏ {len(users)} ᴜꜱᴇʀꜱ...</b>", parse_mode="html")
    
    for user in users:
        try:
            await message.copy_to(chat_id=user)
            count += 1
            await asyncio.sleep(0.05) # Avoid flood
        except:
            pass
            
    await message.answer(f"<tg-emoji emoji-id=\"6111827380915934490\">✅</tg-emoji> <b>ʙʀᴏᴀᴅᴄᴀꜱᴛ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ!</b>\n\nꜱᴇɴᴛ ᴛᴏ <code>{count}</code> ᴜꜱᴇʀꜱ.", parse_mode="html")

@router.callback_query(F.data.startswith("fulfill_token_"))
async def cb_fulfill_token(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        return
        
    data = callback.data.split("_")
    user_id = int(data[2])
    log_msg_id = int(data[3])
    
    # Extract User Name from original message text
    original_text = callback.message.text or callback.message.caption or ""
    import re
    name_match = re.search(r"ᴜꜱᴇʀ: (.*)", original_text)
    user_name = name_match.group(1).strip() if name_match else "User"
    
    await state.update_data(user_id=user_id, user_name=user_name, log_msg_id=log_msg_id, original_msg_id=callback.message.message_id)
    await state.set_state(AdminStates.waiting_for_token)
    
    await callback.message.reply(f"<tg-emoji emoji-id=\"5769289093221454192\">🔗</tg-emoji> <b>Pʟᴇᴀꜱᴇ ꜱᴇɴᴅ ᴛʜᴇ ɴᴇᴛꜰʟɪx ʟᴏɢɪɴ ʟɪɴᴋ ꜰᴏʀ ᴜꜱᴇʀ {user_id}.</b>\n\n<i>Just send the link, it will be sent with the video guide automatically.</i>", parse_mode="html")
    await callback.answer()

@router.message(AdminStates.waiting_for_token)
async def process_token_fulfillment(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ <b>Fulfillment cancelled.</b>", parse_mode="html")
        return
        
    data = await state.get_data()
    user_id = data.get("user_id")
    user_name = data.get("user_name", "User")
    log_msg_id = data.get("log_msg_id")
    original_msg_id = data.get("original_msg_id")
    
    try:
        # 1. Deliver to User with Template
        link = message.text.strip()
        template = (
            f"<tg-emoji emoji-id=\"6105053139453351459\">🎥</tg-emoji> <b>ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴏʀᴅᴇʀ ʜᴀꜱ ᴀʀʀɪᴠᴇᴅ! 🥳</b>\n\n"
            "<b>ɪɴꜱᴛᴀɴᴛ ᴀᴄᴄᴇꜱꜱ ꜱᴛᴇᴘꜱ:</b>\n"
            f"<tg-emoji emoji-id=\"6219525412439984045\">1️⃣</tg-emoji> ᴡᴀᴛᴄʜ ᴛʜᴇ ᴠɪᴅᴇᴏ ɢᴜɪᴅᴇ ᴄᴀʀᴇꜰᴜʟʟʏ\n"
            f"<tg-emoji emoji-id=\"6222029992553875665\">2️⃣</tg-emoji> ʟᴏɢɪɴ ᴜꜱɪɴɢ ᴛʜɪꜱ ʟɪɴᴋ:\n"
            f"{link}\n\n"
            f"<tg-emoji emoji-id=\"6314510813214284503\">⚠️</tg-emoji> <b>ʟɪɴᴋ ᴛɪᴍᴇ ʟɪᴍɪᴛ / ʟɪɴᴋ ᴛɪᴍᴇ:</b>\n"
            "• English: Use this link within 15 minutes. After 15 minutes it can expire and show an error.\n"
            "• Hinglish: Is link ko 15 minutes ke andar use karo. 15 min ke baad expire/error aa sakta hai.\n"
            "• Need help? Ask admin for a fresh link.\n\n"
            f"<tg-emoji emoji-id=\"6219618059179526172\">3️⃣</tg-emoji> ᴅᴏɴᴇ — ɴᴇᴛꜰʟɪx ʀᴇᴀᴅʏ ᴛᴏ ꜱᴛʀᴇᴀᴍ\n\n"
            f"<tg-emoji emoji-id=\"6314510813214284503\">⚠️</tg-emoji> <b>ɪᴍᴘᴏʀᴛᴀɴᴛ:</b>\n"
            "• ꜰᴏʟʟᴏᴡ ᴀʟʟ ꜱᴛᴇᴘꜱ ᴇxᴀᴄᴛʟʏ\n"
            "• ᴅᴏɴ'ᴛ ʟᴏɢᴏᴜᴛ ᴏʀ ᴄʜᴀɴɢᴇ ꜱᴇᴛᴛɪɴɢꜱ\n"
            "• ꜱᴜᴘᴘᴏʀᴛ: <b>@AbdulDevOfficial</b>\n\n"
            f"<tg-emoji emoji-id=\"5082570294137193886\">✨</tg-emoji> <i>*ᴇɴᴊᴏʏ ɴᴇᴛꜰʟɪx ᴘʀᴇᴍɪᴜᴍ ɪɴ 4ᴋ ᴜʜᴅ!*</i>\n"
            "<b>ᴘᴏᴡᴇʀᴇᴅ ʙʏ @NFX_ProBot</b>"
        )
        
        # Send video guide + template
        try:
            await message.bot.send_video(chat_id=user_id, video=config.GUIDE_VIDEO, caption=template, parse_mode="html")
        except Exception as e:
            print(f"Error sending guide video: {e}")
            await message.bot.send_message(chat_id=user_id, text=template, parse_mode="html")
        
        # 2. Update Admin Panel Message
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id, 
                message_id=original_msg_id, 
                text=f"<tg-emoji emoji-id=\"6111827380915934490\">✅</tg-emoji> <b>ᴛʜɪꜱ ᴏʀᴅᴇʀ ʜᴀꜱ ʙᴇᴇɴ ᴄᴏᴍᴘʟᴇᴛᴇᴅ!</b>", 
                parse_mode="html"
            )
        except: pass
        
        # 3. Send Proof to Log Channel
        proof_text = (
            f"<b><tg-emoji emoji-id=\"6111827380915934490\">✅</tg-emoji> ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ ᴅᴇʟɪᴠᴇʀʏ!</b>\n\n"
            f"<tg-emoji emoji-id=\"6035084557378654059\">👤</tg-emoji> ᴜꜱᴇʀ: <code>{user_name}</code>\n"
            f"<tg-emoji emoji-id=\"6201809243574638159\">🆔</tg-emoji> ᴜꜱᴇʀ ɪᴅ: <code>{user_id}</code>\n"
            f"<tg-emoji emoji-id=\"5426875157715105521\">🎁</tg-emoji> ɪᴛᴇᴍ: <b>ɴᴇᴛꜰʟɪx ᴛᴏᴋᴇɴ ʟᴏɢɪɴ</b>\n"
            f"<tg-emoji emoji-id=\"5451732530048802485\">⏳</tg-emoji> ꜱᴛᴀᴛᴜꜱ: <code>COMPLETED FAST <tg-emoji emoji-id=\"6113939237810217462\">⚡</tg-emoji></code>\n\n"
            f"<i><tg-emoji emoji-id=\"5080167990079523335\">🤖</tg-emoji> Delivered via @NFX_ProBot</i>"
        )
        try:
            # Send as reply in the log channel
            await message.bot.send_message(chat_id=config.LOG_CHANNEL_ID, text=proof_text, parse_mode="html", reply_to_message_id=log_msg_id)
        except:
            # Fallback if reply fails
            await message.bot.send_message(chat_id=config.LOG_CHANNEL_ID, text=proof_text, parse_mode="html")
            
        await message.reply(f"<tg-emoji emoji-id=\"6111827380915934490\">✅</tg-emoji> <b>ᴏʀᴅᴇʀ ꜱᴇɴᴛ ᴛᴏ ᴜꜱᴇʀ ᴀɴᴅ ᴍᴀʀᴋᴇᴅ ᴀꜱ ᴄᴏᴍᴘʟᴇᴛᴇ!</b>", parse_mode="html")
        await state.clear()
        
    except Exception as e:
        await message.reply(f"❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ꜱᴇɴᴅ ᴛᴏ ᴜꜱᴇʀ ᴏʀ ᴄʜᴀɴɴᴇʟ: {str(e)}")
        await state.clear()
@router.message(F.content_type.in_({'photo', 'animation', 'video', 'document'}))
async def get_file_id(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return
    if message.chat.type != "private":
        return
    
    file_id = None
    media_type = "File"
    
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "Photo"
    elif message.animation:
        file_id = message.animation.file_id
        media_type = "Animation/GIF"
    elif message.video:
        file_id = message.video.file_id
        media_type = "Video"
    elif message.document:
        file_id = message.document.file_id
        media_type = "Document"
        
    await message.reply(f"<b>🆔 {media_type} ꜰɪʟᴇ ɪᴅ:</b>\n<code>{file_id}</code>\n\n<i>Use this in config.py or for start media.</i>", parse_mode="html")

@router.message(Command("gen_coupon"))
async def cmd_gen_coupon(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return

    env = await get_env(message)
    bot, Bot, libs = env['bot'], env['Bot'], env.get('libs') or BDFTLibs()

    # Usage: /gen_coupon <amount>
    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Usage: <code>/gen_coupon AMOUNT</code>", parse_mode="html")
        return

    try:
        amount = int(args[1])
        # Generate 16 char code
        import string
        import random
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
        
        # Save to DB: Code=<CODE> -> value (amount in points)
        await Bot.saveData(f"Coupon={code}", amount)
        
        admin_msg = (
            f"<b>🎟 Coupon Generated Successfully!</b>\n\n"
            f"🔑 Code: <code>{code}</code>\n"
            f"💰 Value: <b>{amount} Points</b>\n\n"
            f"<i>Send this code to the user or post in channel.</i>"
        )
        await message.answer(admin_msg, parse_mode="html")
        
    except ValueError:
        await message.answer("❌ Amount must be a number.")

@router.message(Command("addnf"))
async def cmd_add_nf_stock(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return
        
    env = await get_env(message)
    Bot = env['Bot']
    
    # Format: /addnf email:pass \n email:pass
    lines = message.text.split("\n")[1:]
    if not lines:
        await message.answer("⚠️ <b>ᴜꜱᴀɢᴇ:</b>\n<code>/addnf\nemail1:pass1\nemail2:pass2</code>", parse_mode="html")
        return
        
    added = 0
    current_nf = await Bot.getData("NF") or 0
    current_nf = int(current_nf)
    
    for line in lines:
        line = line.strip()
        if ":" in line:
            email, password = line.split(":", 1)
            current_nf += 1
            account_data = {"Email": email.strip(), "Pass": password.strip()}
            await Bot.saveData(f"NFAcc{current_nf}", account_data)
            added += 1
            
    if added > 0:
        await Bot.saveData("NF", current_nf)
        await message.answer(f"✅ <b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴀᴅᴅᴇᴅ {added} ɴᴇᴛꜰʟɪx ᴀᴄᴄᴏᴜɴᴛꜱ!</b>\n\n📦 Total Stock ID is now: {current_nf}", parse_mode="html")
    else:
        await message.answer("❌ No valid accounts found. Ensure format is <code>email:password</code>.", parse_mode="html")

from utils.bdft_env import BDFTLibs
