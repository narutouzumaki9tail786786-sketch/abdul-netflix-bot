import html
import time
import uuid
from decimal import Decimal, InvalidOperation

import httpx
from aiogram import F, Router, types
from aiogram.types import InlineKeyboardButton, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from utils.bdft_env import BDFTUser
from utils.db_manager import db

router = Router()

STAR_EMOJI_ID = "6109340839664686978"
USDT_EMOJI_ID = "6282671941476164461"
STAR = f'<tg-emoji emoji-id="{STAR_EMOJI_ID}">🌟</tg-emoji>'
USDT = f'<tg-emoji emoji-id="{USDT_EMOJI_ID}">💲</tg-emoji>'


def _parse_packs(raw: str, money: bool = False):
    packs = []
    for item in (raw or "").split(","):
        if ":" not in item:
            continue
        points_raw, amount_raw = item.split(":", 1)
        try:
            points = int(points_raw.strip())
            if money:
                amount = Decimal(amount_raw.strip())
            else:
                amount = int(amount_raw.strip())
        except (ValueError, InvalidOperation):
            continue
        if points > 0 and amount > 0:
            packs.append((points, amount))
    return packs


def crypto_packs():
    return _parse_packs(config.CRYPTO_PACKS, money=True) or [
        (3, Decimal("0.60")),
        (5, Decimal("1.00")),
        (9, Decimal("1.50")),
        (15, Decimal("2.40")),
    ]


def stars_packs():
    return _parse_packs(config.STARS_PACKS, money=False) or [
        (3, 50),
        (5, 80),
        (9, 130),
        (15, 200),
    ]


def _payment_key(track_id: str) -> str:
    return f"payment:oxapay:{track_id}"


def _stars_payload(order_id: str) -> str:
    return f"stars_points:{order_id}"


def _data_payload(data):
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return data["data"]
    return data if isinstance(data, dict) else {}


async def _credit_points(user_id: int, points: int):
    balance = await BDFTUser.getData("balance", user_id) or 0
    await BDFTUser.saveData("balance", int(balance) + int(points), user_id)
    return int(balance) + int(points)


async def _create_oxapay_invoice(user_id: int, points: int, amount: Decimal):
    if not config.OXAPAY_API_KEY:
        raise RuntimeError("OxaPay API key is not configured.")

    order_id = f"nfx-{user_id}-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    payload = {
        "amount": float(amount),
        "currency": config.PAYMENT_CURRENCY,
        "order_id": order_id,
        "description": f"NFX_ProBot {points} points",
        "thanks_message": "Payment received. Return to Telegram and tap Check Payment.",
        "lifetime": 60,
        "fee_paid_by_payer": 1,
    }
    headers = {
        "merchant_api_key": config.OXAPAY_API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post("https://api.oxapay.com/v1/payment/invoice", json=payload, headers=headers)
        data = response.json()

    if response.status_code >= 400:
        raise RuntimeError(data.get("message") or f"OxaPay HTTP {response.status_code}")

    result = _data_payload(data)
    track_id = str(result.get("track_id") or result.get("trackId") or result.get("id") or "")
    pay_link = result.get("payment_url") or result.get("payLink") or result.get("pay_link") or result.get("url")
    if not track_id or not pay_link:
        raise RuntimeError(data.get("message") or "OxaPay invoice response missing track/payment URL.")

    order = {
        "user_id": user_id,
        "points": points,
        "amount": str(amount),
        "currency": config.PAYMENT_CURRENCY,
        "order_id": order_id,
        "track_id": track_id,
        "paid": False,
        "created_at": int(time.time()),
    }
    await db.save_bot_data(_payment_key(track_id), order)
    return track_id, pay_link


async def _get_oxapay_status(track_id: str):
    headers = {
        "merchant_api_key": config.OXAPAY_API_KEY,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"https://api.oxapay.com/v1/payment/{track_id}", headers=headers)
        data = response.json()
    if response.status_code >= 400:
        raise RuntimeError(data.get("message") or f"OxaPay HTTP {response.status_code}")

    data = _data_payload(data)
    return str(data.get("status", "")).lower() if isinstance(data, dict) else ""


@router.callback_query(F.data == "buy_points_crypto")
async def cb_buy_points_crypto(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for points, amount in crypto_packs():
        kb.add(InlineKeyboardButton(
            text=f"USDT Auto Pay - {points} points - ${amount}",
            callback_data=f"crypto_pack:{points}:{amount}",
            icon_custom_emoji_id=USDT_EMOJI_ID,
        ))
    kb.add(InlineKeyboardButton(text="Back", callback_data="buy_points_back"))
    kb.adjust(1)
    await callback.message.answer(
        f"{USDT} <b>Crypto / USDT Payment</b>\n\nSelect a package. The bot will create an OxaPay payment link.",
        parse_mode="html",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("crypto_pack:"))
async def cb_crypto_pack(callback: types.CallbackQuery):
    try:
        _, points_raw, amount_raw = callback.data.split(":", 2)
        points = int(points_raw)
        amount = Decimal(amount_raw)
        track_id, pay_link = await _create_oxapay_invoice(callback.from_user.id, points, amount)
    except Exception as exc:
        await callback.message.answer(f"Payment link create failed: <code>{html.escape(str(exc))}</code>", parse_mode="html")
        await callback.answer()
        return

    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="Pay Now", url=pay_link, icon_custom_emoji_id=USDT_EMOJI_ID))
    kb.add(InlineKeyboardButton(text="Check Payment", callback_data=f"check_crypto:{track_id}", icon_custom_emoji_id=USDT_EMOJI_ID))
    kb.adjust(1)
    await callback.message.answer(
        f"{USDT} <b>Invoice Created</b>\n\n"
        f"Package: <b>{points} points</b>\n"
        f"Amount: <code>{amount} {config.PAYMENT_CURRENCY}</code>\n\n"
        f"After payment, tap <b>Check Payment</b>.",
        parse_mode="html",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("check_crypto:"))
async def cb_check_crypto(callback: types.CallbackQuery):
    track_id = callback.data.split(":", 1)[1]
    order = await db.get_bot_data(_payment_key(track_id))
    if not order or int(order.get("user_id", 0)) != callback.from_user.id:
        await callback.answer("Invoice not found.", show_alert=True)
        return
    if order.get("paid"):
        await callback.answer("Already credited.", show_alert=True)
        return

    try:
        status = await _get_oxapay_status(track_id)
    except Exception as exc:
        await callback.answer(f"Check failed: {str(exc)[:120]}", show_alert=True)
        return

    if status not in {"paid", "completed", "complete", "success", "confirmed"}:
        await callback.answer(f"Payment status: {status or 'pending'}", show_alert=True)
        return

    points = int(order["points"])
    new_balance = await _credit_points(callback.from_user.id, points)
    order["paid"] = True
    order["paid_at"] = int(time.time())
    order["status"] = status
    await db.save_bot_data(_payment_key(track_id), order)
    await callback.message.answer(
        f"{USDT} <b>Payment confirmed!</b>\n\n"
        f"Added: <b>{points} points</b>\n"
        f"Balance: <b>{new_balance} points</b>",
        parse_mode="html",
    )
    await callback.answer("Points credited.", show_alert=True)


@router.callback_query(F.data == "buy_points_stars")
async def cb_buy_points_stars(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for points, stars in stars_packs():
        kb.add(InlineKeyboardButton(
            text=f"Stars - {points} points - {stars}",
            callback_data=f"stars_pack:{points}:{stars}",
            icon_custom_emoji_id=STAR_EMOJI_ID,
        ))
    kb.add(InlineKeyboardButton(text="Back", callback_data="buy_points_back"))
    kb.adjust(1)
    await callback.message.answer(
        f"{STAR} <b>Telegram Stars Payment</b>\n\nSelect a package.",
        parse_mode="html",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stars_pack:"))
async def cb_stars_pack(callback: types.CallbackQuery):
    _, points_raw, stars_raw = callback.data.split(":", 2)
    points = int(points_raw)
    stars = int(stars_raw)
    order_id = uuid.uuid4().hex
    await db.save_bot_data(f"payment:stars:{order_id}", {
        "user_id": callback.from_user.id,
        "points": points,
        "stars": stars,
        "paid": False,
        "created_at": int(time.time()),
    })
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"NFX_ProBot {points} Points",
        description=f"Add {points} points to your NFX_ProBot balance.",
        payload=_stars_payload(order_id),
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{points} points", amount=stars)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_stars_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("netflix_combo:"):
        from handlers.services import fulfill_paid_combo_order

        order_id = payload.split(":", 1)[1]
        await fulfill_paid_combo_order(message, order_id)
        return
    if not payload.startswith("stars_points:"):
        return
    order_id = payload.split(":", 1)[1]
    key = f"payment:stars:{order_id}"
    order = await db.get_bot_data(key)
    if not order or order.get("paid"):
        return
    if int(order.get("user_id", 0)) != message.from_user.id:
        return

    points = int(order["points"])
    new_balance = await _credit_points(message.from_user.id, points)
    order["paid"] = True
    order["paid_at"] = int(time.time())
    await db.save_bot_data(key, order)
    await message.answer(
        f"{STAR} <b>Stars payment confirmed!</b>\n\n"
        f"Added: <b>{points} points</b>\n"
        f"Balance: <b>{new_balance} points</b>",
        parse_mode="html",
    )


@router.callback_query(F.data == "buy_points_back")
async def cb_buy_points_back(callback: types.CallbackQuery):
    from handlers.store import send_buy_coins_menu

    await send_buy_coins_menu(callback.message)
    await callback.answer()
