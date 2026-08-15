from motor.motor_asyncio import AsyncIOMotorClient
from config import config

class DBManager:
    def __init__(self):
        self.client = AsyncIOMotorClient(config.MONGO_URL)
        self.db = self.client[config.DATABASE_NAME]
        self.bot_data = self.db.bot_data
        self.users = self.db.users

    async def get_bot_data(self, key: str, default=None):
        doc = await self.bot_data.find_one({"_id": key})
        return doc["value"] if doc else default

    async def save_bot_data(self, key: str, value):
        await self.bot_data.update_one(
            {"_id": key},
            {"$set": {"value": value}},
            upsert=True
        )

    async def delete_bot_data(self, key: str):
        await self.bot_data.delete_one({"_id": key})

    async def get_bot_list_data(self, key: str, default=None):
        value = await self.get_bot_data(key, default)
        if value is None:
            return [] if default is None else default
        if isinstance(value, list):
            return value
        return default if default is not None else []

    async def save_bot_list_data(self, key: str, value):
        if value is None:
            value = []
        if not isinstance(value, list):
            value = list(value)
        await self.save_bot_data(key, value)

    async def get_user_data(self, user_id, key: str, default=None):
        user_id = str(user_id)
        doc = await self.users.find_one({"_id": user_id})
        if doc and key in doc:
            return doc[key]
        return default

    async def save_user_data(self, user_id, key: str, value):
        user_id = str(user_id)
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {key: value}},
            upsert=True
        )

    async def get_all_users(self):
        cursor = self.users.find({}, {"_id": 1})
        return [doc["_id"] for doc in await cursor.to_list(length=10000)]

    async def create_netflix_guarantee_order(self, user_id, order: dict):
        order_id = order["order_id"]
        await self.save_bot_data(f"netflix_guarantee:{order_id}", order)

        order_ids = await self.get_user_data(user_id, "netflix_guarantee_order_ids", []) or []
        order_ids = [existing_id for existing_id in order_ids if existing_id != order_id]
        order_ids.insert(0, order_id)
        await self.save_user_data(user_id, "netflix_guarantee_order_ids", order_ids[:50])

    async def get_netflix_guarantee_order(self, order_id: str, default=None):
        return await self.get_bot_data(f"netflix_guarantee:{order_id}", default)

    async def get_netflix_guarantee_orders(self, user_id, limit: int = 10):
        order_ids = await self.get_user_data(user_id, "netflix_guarantee_order_ids", []) or []
        orders = []
        for order_id in order_ids[:limit]:
            order = await self.get_netflix_guarantee_order(order_id)
            if order:
                orders.append(order)
        return orders

db = DBManager()
