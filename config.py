import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    
    # Admins
    ADMIN_ID: int = 7817406686
    ADMINS: list[int] = [7817406686, 8267676849, 8133131791]
    
    # Channels for Force Join
    CHANNELS: list = [
        "@AbdulBotzOfficial",
        "@LootifyXOfficial",
        -1003586753317,
        "@AbdulDevOfficialCommunity",
        "@AbdulBotMakingTips",
        "@NAGIxAbdulBotZOfficial",
    ]
    
    # Log Channel for Orders
    LOG_CHANNEL_ID: int = -1002816424200
    
    # Media Settings
    START_MEDIA: str = "BAACAgQAAxkBAAMbamhgkrZAm2hZdvcSdfKOJ3eWWoUAAp4hAAIkH0hTjNoZ81diV9I9BA"
    START_MEDIA_TYPE: str = "video"
    GUIDE_VIDEO: str = "BAACAgQAAxkBAAICDGpocd_2z65Xxk8NkU8Dw3WBGYrsAALFHQACzovAUah8IwhNaR9QPQQ"
    GUIDE_VIDEO_PC: str = "BAACAgQAAxkBAAICDmpocd-PB-WhAAEcxCILHFSGcHihugACyB0AAs6LwFHFsp2IQ9CHQT0E"
    GUIDE_VIDEO_IPHONE: str = "BAACAgQAAxkBAAICDWpocd8o5AXxQCceAc2Kqyd0VSVyAALGHQACzovAUYYrU5A1lcJ9PQQ"
    
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "netflix_bot")

    # Payments
    OXAPAY_API_KEY: str = os.getenv("OXAPAY_API_KEY", "")
    PAYMENT_CURRENCY: str = os.getenv("PAYMENT_CURRENCY", "USD")
    CRYPTO_PACKS: str = os.getenv("CRYPTO_PACKS", "3:0.60,5:1.00,9:1.50,15:2.40")
    STARS_PACKS: str = os.getenv("STARS_PACKS", "3:50,5:80,9:130,15:200")

    class Config:
        case_sensitive = True

config = Settings()
