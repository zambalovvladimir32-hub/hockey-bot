import asyncio
import aiohttp
import os
import logging
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Это зеркало данных, которое использует мобильное приложение (оно без лимитов)
TEST_URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Origin": "https://www.flashscore.kz",
    "Referer": "https://www.flashscore.kz/"
}

async def check_visibility():
    logger.info("Проверка связи с бесплатным шлюзом данных...")
    
    # SSL=False помогает обойти ошибки сертификатов на Amvera
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        try:
            async with session.get(TEST_URL, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stages = data.get('Stages', [])
                    
                    if not stages:
                        await bot.send_message(CHANNEL_ID, "✅ Связь есть! Но в хоккее сейчас перерыв (матчей в лайве нет).")
                        return

                    text = "🏒 **БОТ ВИДИТ МАТЧИ (БЕЗ ЛИМИТОВ):**\n\n"
                    for stage in stages[:3]: # Берем первые 3 лиги
                        league = stage.get('Snm', 'Лига')
                        for event in stage.get('Events', []):
                            home = event.get('T1', [{}])[0].get('Nm', 'Хозяева')
                            away = event.get('T2', [{}])[0].get('Nm', 'Гости')
                            score = f"{event.get('Tr1', 0)}:{event.get('Tr2', 0)}"
                            text += f"🏆 {league}\n⚔️ {home} — {away} | `{score}`\n\n"
                    
                    await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                else:
                    await bot.send_message(CHANNEL_ID, f"❌ Ошибка зеркала: {resp.status}. Amvera всё еще блокирует прямой доступ.")
        except Exception as e:
            await bot.send_message(CHANNEL_ID, f"🚫 Ошибка сети: {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(check_visibility())
