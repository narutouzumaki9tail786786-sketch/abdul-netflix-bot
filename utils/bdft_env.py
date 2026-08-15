import datetime
import random
import string
import httpx
from aiogram import Bot as TelegramBot
from utils.db_manager import db

class BDFTBot:
    def __init__(self, tg_bot: TelegramBot):
        self._tg_bot = tg_bot

    async def getData(self, key):
        return await db.get_bot_data(key)

    async def saveData(self, key, value):
        await db.save_bot_data(key, value)

    async def deleteData(self, key):
        await db.delete_bot_data(key)

    def info(self):
        from config import config
        class BotInfo:
            def __init__(self, token):
                self.token = token
        return BotInfo(config.BOT_TOKEN)

    async def broadcast(self, code):
        # Basic implementation for compatibility
        # In BDFT this runs code for all users. 
        # Here we just return a status message for now.
        return "Broadcast task started..."

    async def runCommand(self, command_name, user_id=None):
        # Placeholder for running another command
        print(f"Running command: {command_name} for user: {user_id}")
        return True

    async def sendMessage(self, chat_id, text, parse_mode="html", reply_markup=None):
        return await self._tg_bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)

    async def sendPhoto(self, chat_id, photo, caption=None, parse_mode="html", reply_markup=None):
        return await self._tg_bot.send_photo(chat_id, photo, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup)

    async def sendAnimation(self, chat_id, animation, caption=None, parse_mode="html", reply_markup=None):
        return await self._tg_bot.send_animation(chat_id, animation, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup)

    async def sendVideo(self, chat_id, video, caption=None, parse_mode="html", reply_markup=None):
        return await self._tg_bot.send_video(chat_id, video, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup)

    async def handleNextCommand(self, command_name, state=None, options=None):

        if state:
            await state.set_state(f"waiting_for:{command_name}")
            if options:
                await state.update_data(options=options)

class BDFTUser:
    @staticmethod
    async def getData(key, user_id):
        return await db.get_user_data(user_id, key)

    @staticmethod
    async def saveData(key, data, user_id):
        await db.save_user_data(user_id, key, data)

class BDFTHTTP:
    @staticmethod
    async def get(url):
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            return BDFTResponse(resp)

    @staticmethod
    async def post(url, data=None):
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data)
            return BDFTResponse(resp)

class BDFTResponse:
    def __init__(self, resp):
        self._resp = resp
    
    def json(self):
        return self._resp.json()
    
    @property
    def text(self):
        return self._resp.text

class BDFTLibs:
    class dateandtime:
        @staticmethod
        def now(timezone="UTC"):
            now = datetime.datetime.now()
            return {
                "time": now.strftime("%H:%M:%S"),
                "date": now.strftime("%Y-%m-%d"),
                "full": now.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    class Random:
        @staticmethod
        def randomStr(length, charset=None):
            if not charset:
                charset = string.ascii_letters + string.digits
            return "".join(random.choices(charset, k=length))

def bunchify(data):
    if isinstance(data, dict):
        return type("Bunch", (), {k: bunchify(v) for k, v in data.items()})
    elif isinstance(data, list):
        return [bunchify(v) for v in data]
    else:
        return data
