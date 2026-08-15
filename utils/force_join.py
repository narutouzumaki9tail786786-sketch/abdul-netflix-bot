import html
from typing import Any

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from utils.db_manager import db


FORCE_JOIN_CHANNELS_KEY = "force_join_channels"
NUMBER_ICON_IDS = [
    "6219525412439984045",  # 1
    "6222029992553875665",  # 2
    "6219618059179526172",  # 3
    "6219826747345471627",  # 4
    "6219909202127620214",  # 5
    "6221746649266391336",  # 6
    "6220028211376425519",  # 7
    "6222219718439209089",  # 8
    "6222084349659973777",  # 9
    "6219488394116859803",  # 0
]
CHANNEL_ICON_1 = NUMBER_ICON_IDS[0]
CHANNEL_ICON_2 = NUMBER_ICON_IDS[1]
CHANNEL_ICON_3 = NUMBER_ICON_IDS[2]
CHANNEL_ICON_4 = NUMBER_ICON_IDS[3]
CHANNEL_ICON_5 = NUMBER_ICON_IDS[4]
CHANNEL_ICON_6 = NUMBER_ICON_IDS[5]

DEFAULT_CHANNEL_BUTTONS = [
    {
        "chat_id": "@AbdulBotzOfficial",
        "url": "https://t.me/AbdulBotzOfficial",
        "label": "ᴄʜᴀɴɴᴇʟ",
        "icon": CHANNEL_ICON_1,
    },
    {
        "chat_id": "@LootifyXOfficial",
        "url": "https://t.me/LootifyXOfficial",
        "label": "ᴄʜᴀɴɴᴇʟ",
        "icon": CHANNEL_ICON_2,
    },
    {
        "chat_id": -1003586753317,
        "url": "https://t.me/+Y-PcTNYWdBtmOTll",
        "label": "ᴘʀɪᴠᴀᴛᴇ",
        "icon": CHANNEL_ICON_3,
    },
    {
        "chat_id": "@AbdulDevOfficialCommunity",
        "url": "https://t.me/AbdulDevOfficialCommunity",
        "label": "ᴄᴏᴍᴍᴜɴɪᴛʏ",
        "icon": CHANNEL_ICON_4,
    },
    {
        "chat_id": "@AbdulBotMakingTips",
        "url": "https://t.me/AbdulBotMakingTips",
        "label": "ᴄʜᴀɴɴᴇʟ",
        "icon": CHANNEL_ICON_5,
    },
    {
        "chat_id": "@NAGIxAbdulBotZOfficial",
        "url": "https://t.me/NAGIxAbdulBotZOfficial",
        "label": "ᴄʜᴀɴɴᴇʟ",
        "icon": CHANNEL_ICON_6,
    },
]


def _default_channel_items() -> list[dict[str, Any]]:
    configured = list(config.CHANNELS or [])
    items = list(DEFAULT_CHANNEL_BUTTONS)
    known = {item["chat_id"] for item in items}
    for channel in configured:
        if channel in known:
            continue
        if isinstance(channel, str) and channel.startswith("@"):
            url = f"https://t.me/{channel[1:]}"
        else:
            url = None
        items.append(
            {
                "chat_id": channel,
                "url": url,
                "label": "ᴄʜᴀɴɴᴇʟ",
                "icon": CHANNEL_ICON_1,
            }
        )
    return items


def normalize_public_channel(raw: str) -> dict[str, Any] | None:
    value = (raw or "").strip().strip("/")
    if not value:
        return None
    if value.startswith("https://t.me/"):
        value = value.removeprefix("https://t.me/").strip("/")
    elif value.startswith("http://t.me/"):
        value = value.removeprefix("http://t.me/").strip("/")
    elif value.startswith("t.me/"):
        value = value.removeprefix("t.me/").strip("/")
    if value.startswith("+") or value.lstrip("-").isdigit():
        return None
    username = value if value.startswith("@") else f"@{value}"
    if len(username) < 2:
        return None
    return {
        "chat_id": username,
        "url": f"https://t.me/{username[1:]}",
        "label": "ᴄʜᴀɴɴᴇʟ",
        "icon": CHANNEL_ICON_1,
        "kind": "public",
    }


def normalize_button_url(raw: str) -> str | None:
    value = (raw or "").strip()
    if not value:
        return None
    if value.startswith("http://t.me/"):
        return "https://t.me/" + value.removeprefix("http://t.me/").strip("/")
    if value.startswith("https://t.me/"):
        return value.rstrip("/")
    if value.startswith("t.me/"):
        return "https://" + value.strip("/")
    if value.startswith("@"):
        return f"https://t.me/{value[1:]}"
    if "/" not in value and " " not in value:
        return f"https://t.me/{value.lstrip('@')}"
    return None


def normalize_private_channel(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if "|" in text:
        chat_id_raw, invite_url = [part.strip() for part in text.split("|", 1)]
    else:
        parts = text.split()
        if len(parts) != 2:
            return None
        chat_id_raw, invite_url = parts
    if not chat_id_raw.lstrip("-").isdigit():
        return None
    if not (invite_url.startswith("https://t.me/+") or invite_url.startswith("https://t.me/joinchat/")):
        return None
    return {
        "chat_id": int(chat_id_raw),
        "url": invite_url,
        "label": "ᴘʀɪᴠᴀᴛᴇ",
        "icon": CHANNEL_ICON_4,
        "kind": "private",
    }


def _coerce_item(item: Any) -> dict[str, Any] | None:
    if isinstance(item, dict) and "chat_id" in item:
        return item
    if isinstance(item, str):
        public = normalize_public_channel(item)
        if public:
            return public
        return {"chat_id": item, "url": None, "label": "ᴄʜᴀɴɴᴇʟ", "icon": CHANNEL_ICON_1}
    if isinstance(item, int):
        return {"chat_id": item, "url": None, "label": "ᴘʀɪᴠᴀᴛᴇ", "icon": CHANNEL_ICON_4}
    return None


async def get_extra_force_join_items() -> list[dict[str, Any]]:
    stored = await db.get_bot_data(FORCE_JOIN_CHANNELS_KEY, [])
    if not isinstance(stored, list):
        return []
    items = []
    seen = set()
    for raw in stored:
        item = _coerce_item(raw)
        if not item:
            continue
        chat_id = item["chat_id"]
        if chat_id in seen:
            continue
        seen.add(chat_id)
        items.append(item)
    return items


async def save_extra_force_join_items(items: list[dict[str, Any]]):
    cleaned = []
    seen = set()
    for item in items:
        coerced = _coerce_item(item)
        if not coerced:
            continue
        chat_id = coerced["chat_id"]
        if chat_id in seen:
            continue
        seen.add(chat_id)
        cleaned.append(coerced)
    await db.save_bot_data(FORCE_JOIN_CHANNELS_KEY, cleaned)


async def get_all_force_join_items() -> list[dict[str, Any]]:
    items = []
    seen = set()
    for source in (_default_channel_items(), await get_extra_force_join_items()):
        for item in source:
            chat_id = item["chat_id"]
            if chat_id in seen:
                continue
            seen.add(chat_id)
            items.append(item)
    return items


async def get_force_join_chat_ids() -> list[Any]:
    return [item["chat_id"] for item in await get_all_force_join_items()]


def build_force_join_keyboard(items: list[dict[str, Any]]):
    kb = InlineKeyboardBuilder()
    visible_index = 0
    for item in items:
        if not item.get("url"):
            continue
        icon_id = NUMBER_ICON_IDS[visible_index % len(NUMBER_ICON_IDS)]
        visible_index += 1
        kb.add(
            InlineKeyboardButton(
                text=item.get("label") or "ᴄʜᴀɴɴᴇʟ",
                url=item["url"],
                icon_custom_emoji_id=icon_id,
                style="primary",
            )
        )
    kb.add(
        InlineKeyboardButton(
            text="ᴠᴇʀɪꜰʏ",
            callback_data="verify_join",
            icon_custom_emoji_id="6111827380915934490",
            style="success",
        )
    )
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def render_channel_list(items: list[dict[str, Any]], *, extras_only: bool = False) -> str:
    if not items:
        return "<b>No extra force channels added yet.</b>"
    title = "Extra Force-Join Channels" if extras_only else "Force-Join Channels"
    lines = [f"<b>{title}</b>", ""]
    for idx, item in enumerate(items, start=1):
        chat_id = html.escape(str(item.get("chat_id")))
        kind = html.escape(str(item.get("kind") or "default"))
        url = html.escape(str(item.get("url") or "no public button url"))
        lines.append(f"{idx}. <b>{kind}</b> | <code>{chat_id}</code>")
        lines.append(f"   <code>{url}</code>")
    return "\n".join(lines)
