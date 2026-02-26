import asyncio
import aiohttp
import os
from aiogram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

async def test_connection():
    # Проверяем 3 разных пути
    targets = {
        "Google": "https://www.google.com",
        "Flashscore Core": "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8",
        "Зеркало": "https://v3.ls-api.com/get/hockey/live"
    }
    
    report = "🔍 **ОТЧЕТ О ПРОВЕРКЕ СВЯЗИ:**\n\n"
    
    async with aiohttp.ClientSession() as session:
        for name, url in targets.items():
            try:
                async with session.get(url, timeout=10) as resp:
                    report += f"✅ {name}: Доступен (Код {resp.status})\n"
            except Exception as e:
                report += f"❌ {name}: Ошибка ({str(e)[:40]})\n"
    
    await bot.send_message(CHANNEL_ID, report)

if __name__ == "__main__":
    asyncio.run(test_connection())
