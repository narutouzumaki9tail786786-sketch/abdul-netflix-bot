from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import html
import uuid

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from utils.bdft_env import BDFTBot, BDFTLibs, BDFTUser
from utils.db_manager import db

router = Router()

CLAIM_CONTACT = "@apifounder"
GUARANTEE_DAYS = 14
DISPLAY_TZ = ZoneInfo("Asia/Kolkata")

MANUAL_PRODUCT_TYPES = {
    "mobile": "Mobile Token Login",
    "iphone": "iPhone Token Login",
    "pc": "PC Token Login",
    "tv": "TV Login",
    "combo": "iOS + Android + TV + PC Combo Login",
}
COMBO_STARS_PRICE = 100
COMBO_PAYMENT_KEY_PREFIX = "payment:netflix_combo:"


async def get_env(message: types.Message):
    return {
        "u": message.from_user.id,
        "bot": BDFTBot(message.bot),
        "Bot": BDFTBot(message.bot),
        "User": BDFTUser(),
        "libs": BDFTLibs(),
        "message": message,
    }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def build_order_id() -> str:
    return f"nfg-{uuid.uuid4().hex[:10]}"


def format_display_dt(value) -> str:
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
    else:
        dt = value
    return dt.astimezone(DISPLAY_TZ).strftime("%d %b %Y, %I:%M %p IST")


def build_netflix_guarantee_order(user_id: int, product_type: str, delivery_mode: str) -> dict:
    delivered_at = now_utc()
    expires_at = delivered_at + timedelta(days=GUARANTEE_DAYS)
    return {
        "order_id": build_order_id(),
        "user_id": int(user_id),
        "product_type": product_type,
        "delivery_mode": delivery_mode,
        "delivered_at": delivered_at.isoformat(),
        "guarantee_expires_at": expires_at.isoformat(),
        "claim_contact": CLAIM_CONTACT,
        "proof_required": True,
        "replacement_events": [],
    }


async def persist_netflix_guarantee_order(order: dict):
    await db.create_netflix_guarantee_order(order["user_id"], order)


def render_guarantee_notice(order: dict) -> str:
    return (
        "<tg-emoji emoji-id=\"5465665476971471368\">🛡</tg-emoji> <b>14 ᴅᴀʏꜱ ɢᴜᴀʀᴀɴᴛᴇᴇ</b>\n"
        f"• ᴠᴀʟɪᴅ ᴜɴᴛɪʟ: <code>{format_display_dt(order['guarantee_expires_at'])}</code>\n"
        f"• ɪꜰ ʟᴏɢɢᴇᴅ ᴏᴜᴛ, ʙʀɪɴɢ ᴘʀᴏᴏꜰ ᴛᴏ <b>{CLAIM_CONTACT}</b>\n"
        "• ᴜɴʟɪᴍɪᴛᴇᴅ ʀᴇᴘʟᴀᴄᴇᴍᴇɴᴛꜱ ᴡɪᴛʜɪɴ 14 ᴅᴀʏꜱ"
    )


def render_menu_guarantee_blurb() -> str:
    return (
        "<tg-emoji emoji-id=\"5465665476971471368\">🛡</tg-emoji> <b>14 ᴅᴀʏꜱ ɢᴜᴀʀᴀɴᴛᴇᴇ</b>\n"
        f"ɪꜰ ʟᴏɢɢᴇᴅ ᴏᴜᴛ, ʙʀɪɴɢ ᴘʀᴏᴏꜰ ᴛᴏ <b>{CLAIM_CONTACT}</b>"
    )


async def process_purchase(
    callback: types.CallbackQuery,
    product_name: str,
    cost: int,
    stock_key: str,
    acc_prefix: str,
    photo_url: str,
    guarantee_product_type: str | None = None,
):
    env = await get_env(callback.message)
    u, bot, Bot, User = env["u"], env["bot"], env["Bot"], env["User"] or BDFTUser()
    u = callback.from_user.id

    try:
        await callback.message.delete()
    except Exception:
        pass

    balance = int(await User.getData("balance", u) or 0)
    if balance < cost:
        await bot.sendMessage(
            u,
            f"<tg-emoji emoji-id=\"5765005318610228026\">❌</tg-emoji> <b>ʏᴏᴜ ɴᴇᴇᴅ ᴀᴛ ʟᴇᴀꜱᴛ {cost} ᴘᴏɪɴᴛꜱ ᴛᴏ ᴘᴜʀᴄʜᴀꜱᴇ {product_name}.</b>",
            parse_mode="html",
        )
        return

    current_index = int(await Bot.getData(stock_key) or 0)
    next_index = current_index + 1
    acc_key = f"{acc_prefix}{next_index}"
    account = await Bot.getData(acc_key)

    if account is None:
        await bot.sendMessage(
            u,
            "<tg-emoji emoji-id=\"5765005318610228026\">❌</tg-emoji> <b>ꜱᴏʀʀʏ, ɴᴇᴛꜰʟɪx ᴘʀᴇᴍɪᴜᴍ (ᴇᴍᴀɪʟ/ᴘᴀꜱꜱ) ɪꜱ ᴄᴜʀʀᴇɴᴛʟʏ ᴏᴜᴛ ᴏꜰ ꜱᴛᴏᴄᴋ.</b>\n\n"
            "<i>ᴛᴏᴋᴇɴ ʟᴏɢɪɴ ʟᴇʟᴏ ᴡᴏ ʙᴀᴛᴛᴇʀ ʀᴀʜᴇɢᴀ <tg-emoji emoji-id=\"6113939237810217462\">⚡</tg-emoji></i>",
            parse_mode="html",
        )
        return

    email = account.get("Email", "Unknown")
    password = account.get("Pass", "Unknown")
    guarantee_order = build_netflix_guarantee_order(
        u,
        guarantee_product_type or product_name,
        "auto_stock",
    )
    caption = (
        f"<b>✨ ʏᴏᴜʀ {product_name} ᴅᴇᴛᴀɪʟꜱ ✨</b>\n\n"
        f"<b>🌐 ᴇᴍᴀɪʟ:</b> <code>{email}</code>\n"
        f"<b>🔑 ᴘᴀꜱꜱᴡᴏʀᴅ:</b> <code>{password}</code>\n\n"
        f"{render_guarantee_notice(guarantee_order)}"
    )

    await User.saveData("balance", balance - cost, u)
    try:
        await bot.sendPhoto(chat_id=u, photo=photo_url, caption=caption, parse_mode="html")
        await Bot.saveData(stock_key, next_index)
        await persist_netflix_guarantee_order(guarantee_order)
    except Exception:
        await User.saveData("balance", balance, u)
        raise


@router.message(Command("netflix"))
@router.message(F.text == "ᴡɪᴛʜᴅʀᴀᴡ ɴᴇᴛꜰʟɪx")
async def cmd_netflix(message: types.Message):
    env = await get_env(message)
    u, bot = env["u"], env["bot"]
    kb = InlineKeyboardBuilder()
    kb.add(
        InlineKeyboardButton(
            text="ᴍᴏʙɪʟᴇ ᴛᴏᴋᴇɴ ʟᴏɢɪɴ (3 ᴘᴏɪɴᴛꜱ)",
            callback_data="buy_netflix_mobile_token",
            icon_custom_emoji_id="5819099456745770209",
            style="success",
        )
    )
    kb.add(
        InlineKeyboardButton(
            text="ɪᴘʜᴏɴᴇ ᴛᴏᴋᴇɴ ʟᴏɢɪɴ (4 ᴘᴏɪɴᴛꜱ)",
            callback_data="buy_netflix_iphone_token",
            icon_custom_emoji_id="5947203453418740129",
            style="success",
        )
    )
    kb.add(
        InlineKeyboardButton(
            text="ᴘᴄ ᴛᴏᴋᴇɴ ʟᴏɢɪɴ (5 ᴘᴏɪɴᴛꜱ)",
            callback_data="buy_netflix_pc_token",
            icon_custom_emoji_id="5334734580068919740",
            style="success",
        )
    )
    kb.add(
        InlineKeyboardButton(
            text="ᴇᴍᴀɪʟ & ᴘᴀꜱꜱᴡᴏʀᴅ (7 ᴘᴏɪɴᴛꜱ)",
            callback_data="buy_netflix_email",
            icon_custom_emoji_id="5303366226293040224",
            style="primary",
        )
    )
    kb.add(
        InlineKeyboardButton(
            text="ᴛᴠ ʟᴏɢɪɴ (8 ᴘᴏɪɴᴛꜱ)",
            callback_data="buy_netflix_tv",
            icon_custom_emoji_id="6105053139453351459",
            style="primary",
        )
    )
    kb.add(
        InlineKeyboardButton(
            text="ɪᴏꜱ + ᴀɴᴅʀᴏɪᴅ + ᴛᴠ + ᴘᴄ (100 ꜱᴛᴀʀꜱ)",
            callback_data="buy_netflix_combo_stars",
            icon_custom_emoji_id="6109340839664686978",
            style="danger",
        )
    )
    kb.add(
        InlineKeyboardButton(
            text="ɴᴇᴛꜰʟɪx ʟɪɴᴋ ʜᴇʟᴘ",
            callback_data="netflix_link_help",
            icon_custom_emoji_id="6026162407066309019",
            style="primary",
        )
    )
    kb.adjust(1)
    caption = (
        "<b><tg-emoji emoji-id=\"5303310030940952439\">💖</tg-emoji> ᴄʜᴏᴏꜱᴇ ʏᴏᴜʀ ᴘʀᴇꜰᴇʀʀᴇᴅ ʟᴏɢɪɴ ᴍᴇᴛʜᴏᴅ:\n\n"
        "<tg-emoji emoji-id=\"5350452584119279096\">💰</tg-emoji> ᴘʀɪᴄᴇꜱ ᴠᴀʀʏ ʙʏ ᴍᴇᴛʜᴏᴅ.\n\n"
        f"{render_menu_guarantee_blurb()}</b>"
    )
    await bot.sendPhoto(
        u,
        photo="https://graph.org/file/6429566fc66b8a523ce78.jpg",
        caption=caption,
        parse_mode="html",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data == "netflix_link_help")
async def cb_netflix_link_help(callback: types.CallbackQuery):
    from handlers.user import NETFLIX_HELP_TEXT

    await callback.message.answer(NETFLIX_HELP_TEXT, parse_mode="html")
    await callback.answer()


async def queue_manual_netflix_order(
    bot,
    user: types.User,
    product_type: str,
    login_type_html: str,
    delivery_key: str,
    paid_note: str | None = None,
):
    u = user.id
    safe_name = html.escape(user.full_name)
    paid_line = f"\n{paid_note}\n" if paid_note else "\n"
    log_text = (
        "<b><tg-emoji emoji-id=\"6201809243574638159\">📥</tg-emoji> ɴᴇᴡ ɴᴇᴛꜰʟɪx ᴍᴀɴᴜᴀʟ ᴏʀᴅᴇʀ</b>\n\n"
        f"<tg-emoji emoji-id=\"6035084557378654059\">👤</tg-emoji> ᴜꜱᴇʀ: <code>{safe_name}</code>\n"
        f"<tg-emoji emoji-id=\"6201809243574638159\">🆔</tg-emoji> ɪᴅ: <code>{u}</code>\n"
        f"<tg-emoji emoji-id=\"5377624166436445368\">🎫</tg-emoji> ᴛʏᴘᴇ: <b>{login_type_html}</b>\n"
        f"<tg-emoji emoji-id=\"5465665476971471368\">🛡</tg-emoji> ɢᴜᴀʀᴀɴᴛᴇᴇ: <b>{GUARANTEE_DAYS} ᴅᴀʏꜱ</b>\n"
        f"<tg-emoji emoji-id=\"5769289093221454192\">🔗</tg-emoji> ᴄʟᴀɪᴍ: <b>{CLAIM_CONTACT}</b>\n"
        f"{paid_line}"
        "<tg-emoji emoji-id=\"6008233706039284019\">⚠️</tg-emoji> <b>ꜱᴛᴀᴛᴜꜱ: ᴘᴇɴᴅɪɴɢ</b>\n\n"
        f"<i>ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪᴛʜ ᴛʜᴇ {product_type} ᴅᴇᴛᴀɪʟꜱ ᴛᴏ ᴄᴏᴍᴘʟᴇᴛᴇ ᴛʜᴇ ᴏʀᴅᴇʀ.</i>"
    )

    log_msg = await bot.send_message(
        chat_id=config.LOG_CHANNEL_ID,
        text=log_text,
        parse_mode="html",
    )
    log_msg_id = log_msg.message_id

    kb = InlineKeyboardBuilder()
    kb.add(
        InlineKeyboardButton(
            text="🛠 ꜰᴜʟꜰɪʟʟ ᴏʀᴅᴇʀ",
            callback_data=f"fulfill_token_{u}_{log_msg_id}_{delivery_key}",
        )
    )

    for admin_id in config.ADMINS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=log_text,
                parse_mode="html",
                reply_markup=kb.as_markup(),
            )
        except Exception:
            pass

    await bot.send_message(
        u,
        "✅ <b>ʏᴏᴜʀ ᴏʀᴅᴇʀ ʜᴀꜱ ʙᴇᴇɴ ꜱᴇɴᴛ ᴛᴏ ᴀᴅᴍɪɴꜱ!</b>\n\n"
        f"ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ꜰᴏʀ ᴅᴇʟɪᴠᴇʀʏ. <b>{GUARANTEE_DAYS} ᴅᴀʏꜱ ɢᴜᴀʀᴀɴᴛᴇᴇ</b> ᴡɪʟʟ ꜱᴛᴀʀᴛ ᴀꜰᴛᴇʀ ʏᴏᴜ ʀᴇᴄᴇɪᴠᴇ ɪᴛ.",
        parse_mode="html",
    )


async def send_manual_netflix_order(
    callback: types.CallbackQuery,
    product_type: str,
    cost: int,
    login_type_html: str,
    delivery_key: str,
):
    env = await get_env(callback.message)
    u, bot, User = callback.from_user.id, env["bot"], env["User"] or BDFTUser()

    try:
        await callback.message.delete()
    except Exception:
        pass

    balance = int(await User.getData("balance", u) or 0)
    if balance < cost:
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username
        ref_link = f"https://t.me/{bot_username}?start={u}"
        needed = cost - balance
        fomo_msg = (
            "<tg-emoji emoji-id=\"5765005318610228026\">❌</tg-emoji> <b>ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴘᴏɪɴᴛꜱ!</b>\n\n"
            f"ʏᴏᴜ ʜᴀᴠᴇ <b>{balance} ᴘᴏɪɴᴛꜱ</b> ʙᴜᴛ ɴᴇᴇᴅ <b>{cost}</b>. ʏᴏᴜ'ʀᴇ <code>{needed}</code> ꜱʜᴏʀᴛ!\n\n"
            "<tg-emoji emoji-id=\"5080213825970505261\">🎉</tg-emoji> <b>ᴇᴀʀɴ ᴘᴏɪɴᴛꜱ ǫᴜɪᴄᴋʟʏ ʙʏ ʀᴇꜰᴇʀʀɪɴɢ!</b>\n"
            "<i>Every friend you invite = 1 Free Point!\n"
            "3 Points = 1 FREE Netflix Account 🎬</i>\n\n"
            "<tg-emoji emoji-id=\"5296258364655805333\">🎬</tg-emoji> <b>Don't miss out — accounts sell out fast!</b>\n\n"
            f"<tg-emoji emoji-id=\"5769289093221454192\">🔗</tg-emoji> <b>ʏᴏᴜʀ ʀᴇꜰᴇʀʀᴀʟ ʟɪɴᴋ:</b>\n<code>{ref_link}</code>"
        )
        kb_fomo = InlineKeyboardBuilder()
        kb_fomo.add(
            InlineKeyboardButton(
                text="ꜱʜᴀʀᴇ ʀᴇꜰᴇʀʀᴀʟ ʟɪɴᴋ",
                url=f"https://t.me/share/url?url={ref_link}&text=Get%20FREE%20Netflix%20Premium!",
                style="success",
                icon_custom_emoji_id="5080213825970505261",
            )
        )
        await callback.message.answer(fomo_msg, parse_mode="html", reply_markup=kb_fomo.as_markup())
        return

    await User.saveData("balance", balance - cost, u)
    try:
        await queue_manual_netflix_order(callback.bot, callback.from_user, product_type, login_type_html, delivery_key)
    except Exception as exc:
        await User.saveData("balance", balance, u)
        await bot.sendMessage(
            u,
            "❌ ᴇʀʀᴏʀ ꜱᴇɴᴅɪɴɢ ʀᴇQᴜᴇꜱᴛ ᴛᴏ ᴀᴅᴍɪɴꜱ.\nᴘᴏɪɴᴛꜱ ʀᴇꜰᴜɴᴅᴇᴅ.",
            parse_mode="html",
        )
        print(f"Token Login Error: {exc}")


def netflix_combo_payment_payload(order_id: str) -> str:
    return f"netflix_combo:{order_id}"


@router.callback_query(F.data == "buy_netflix_combo_stars")
async def cb_buy_netflix_combo_stars(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

    msg_text = (
        "<tg-emoji emoji-id=\"6109340839664686978\">🌟</tg-emoji> <b>ʙᴜʏ ɴᴇᴛꜰʟɪx ᴄᴏᴍʙᴏ (ɪᴏꜱ + ᴀɴᴅʀᴏɪᴅ + ᴛᴠ + ᴘᴄ)</b>\n\n"
        f"<tg-emoji emoji-id=\"6109340839664686978\">⭐</tg-emoji> <b>ᴘʀɪᴄᴇ:</b> <code>{COMBO_STARS_PRICE} Telegram Stars</code>\n\n"
        "<tg-emoji emoji-id=\"5303310030940952439\">⚡</tg-emoji> <b>ɪɴꜱᴛᴀɴᴛ ᴅᴇʟɪᴠᴇʀʏ:</b> Send 100 Stars / Gift directly to Admin in DM to get your account delivered instantly without any delay!\n\n"
        "<tg-emoji emoji-id=\"6201809243574638159\">👇</tg-emoji> <i>Click the button below to message Admin directly:</i>"
    )
    dm_url = "https://t.me/apifounder?text=Hey%20Admin,%20I%20want%20to%20buy%20Netflix%20Combo%20Plan%20(100%20Stars)!"
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="ʙᴜʏ ᴠɪᴀ ᴅᴍ (@apifounder)", url=dm_url, icon_custom_emoji_id="6109340839664686978"))
    await callback.message.answer(msg_text, parse_mode="html", reply_markup=kb.as_markup())
    await callback.answer()


async def fulfill_paid_combo_order(message: types.Message, order_id: str) -> bool:
    key = f"{COMBO_PAYMENT_KEY_PREFIX}{order_id}"
    order = await db.get_bot_data(key)
    if not order or order.get("paid"):
        return False
    if int(order.get("user_id", 0)) != message.from_user.id:
        return False

    order["paid"] = True
    order["paid_at"] = int(datetime.now().timestamp())
    await db.save_bot_data(key, order)
    await queue_manual_netflix_order(
        message.bot,
        message.from_user,
        MANUAL_PRODUCT_TYPES["combo"],
        "<tg-emoji emoji-id=\"6109340839664686978\">🌟</tg-emoji> ɪᴏꜱ + ᴀɴᴅʀᴏɪᴅ + ᴛᴠ + ᴘᴄ ᴄᴏᴍʙᴏ",
        "combo",
        paid_note=f"<tg-emoji emoji-id=\"6109340839664686978\">🌟</tg-emoji> ᴘᴀɪᴅ: <b>{COMBO_STARS_PRICE} Telegram Stars</b>",
    )
    await message.answer(
        "✅ <b>50 Stars payment confirmed!</b>\n\n"
        "Your combo order has been sent to admins for delivery.",
        parse_mode="html",
    )
    return True


@router.callback_query(F.data == "buy_netflix_mobile_token")
async def cb_buy_netflix_mobile_token(callback: types.CallbackQuery):
    await send_manual_netflix_order(
        callback,
        MANUAL_PRODUCT_TYPES["mobile"],
        3,
        "<tg-emoji emoji-id=\"6206056639812867942\">🔑</tg-emoji> ᴍᴏʙɪʟᴇ ᴛᴏᴋᴇɴ ʟᴏɢɪɴ",
        "mobile",
    )


@router.callback_query(F.data == "buy_netflix_iphone_token")
async def cb_buy_netflix_iphone_token(callback: types.CallbackQuery):
    await send_manual_netflix_order(
        callback,
        MANUAL_PRODUCT_TYPES["iphone"],
        4,
        "<tg-emoji emoji-id=\"6206056639812867942\">🔑</tg-emoji> ɪᴘʜᴏɴᴇ ᴛᴏᴋᴇɴ ʟᴏɢɪɴ",
        "iphone",
    )


@router.callback_query(F.data == "buy_netflix_pc_token")
async def cb_buy_netflix_pc_token(callback: types.CallbackQuery):
    await send_manual_netflix_order(
        callback,
        MANUAL_PRODUCT_TYPES["pc"],
        5,
        "<tg-emoji emoji-id=\"6206056639812867942\">🔑</tg-emoji> ᴘᴄ ᴛᴏᴋᴇɴ ʟᴏɢɪɴ",
        "pc",
    )


@router.callback_query(F.data == "buy_netflix_email")
async def cb_buy_netflix_email(callback: types.CallbackQuery):
    await process_purchase(
        callback,
        "Netflix Premium (Email/Pass)",
        7,
        "Apma",
        "NFAcc",
        "https://graph.org/file/68a16fb1e9f131958b1f1.jpg",
        guarantee_product_type="Email & Password",
    )


@router.callback_query(F.data == "buy_netflix_tv")
async def cb_buy_netflix_tv(callback: types.CallbackQuery):
    await send_manual_netflix_order(
        callback,
        MANUAL_PRODUCT_TYPES["tv"],
        8,
        "<tg-emoji emoji-id=\"6105053139453351459\">📺</tg-emoji> ᴛᴠ ʟᴏɢɪɴ",
        "tv",
    )


@router.message(Command("amazonprime"))
async def cmd_amazon(message: types.Message):
    env = await get_env(message)
    u, bot = env["u"], env["bot"]
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="🎉 ᴄᴏɴꜰɪʀᴍ", callback_data="buy_amazon"))
    await bot.sendPhoto(
        u,
        photo="https://graph.org/file/a8ac65589d9b98e8d3617.jpg",
        caption="<b>❣️ ʙᴜʏ ᴀᴍᴀᴢᴏɴ ᴘʀɪᴍᴇ (5 ᴘᴏɪɴᴛꜱ)</b>",
        parse_mode="html",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data == "buy_amazon")
async def cb_buy_amazon(callback: types.CallbackQuery):
    await process_purchase(callback, "Amazon Prime", 5, "AmazonIdx", "AmzAcc", "https://graph.org/file/a8ac65589d9b98e8d3617.jpg")


@router.message(Command("youtubepremium"))
async def cmd_youtube(message: types.Message):
    env = await get_env(message)
    u, bot = env["u"], env["bot"]
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="🎉 ᴄᴏɴꜰɪʀᴍ", callback_data="buy_youtube"))
    await bot.sendPhoto(
        u,
        photo="https://graph.org/file/fa65a3b166a53d4333fe7.jpg",
        caption="<b>ʙᴜʏ ʏᴏᴜᴛᴜʙᴇ ᴘʀᴇᴍɪᴜᴍ (2 ᴘᴏɪɴᴛꜱ)</b>",
        parse_mode="html",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data == "buy_youtube")
async def cb_buy_youtube(callback: types.CallbackQuery):
    await process_purchase(callback, "YouTube Premium", 2, "YTIdx", "YTAcc", "https://graph.org/file/fa65a3b166a53d4333fe7.jpg")
