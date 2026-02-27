import asyncio
import os
import logging
import sys
from aiogram import Bot
import aiohttp

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL")

bot = Bot(token=TOKEN)
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    headers = {
        "x-fsign": "SW9D1eZo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        async with aiohttp.ClientSession() as session:
            # Передаем прокси напрямую
            async with session.get(URL, headers=headers, proxy=PROXY_URL, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.text()
                    return data
                logger.warning(f"Статус сайта: {resp.status}")
    except Exception as e:
        logger.error(f"Ошибка прокси: {e}")
    return None

def parse(data):
    matches = []
    # Быстрый поиск 2-го периода
    if "TT÷2" in data or "NS÷2" in data:
        for block in data.split('~AA÷')[1:]:
            if "TT÷2" in block or "NS÷2" in block:
                try:
                    home = block.split('AE÷')[1].split('¬')[0]
                    away = block.split('AF÷')[1].split('¬')[0]
                    matches.append(f"🏒 **{home} vs {away}** (2-й период)")
                except: continue
    return matches

async def main():
    logger.info(f"🚀 ТЕСТОВЫЙ ЗАПУСК. Прокси: {PROXY_URL}")
    while True:
        data = await get_data()
        if data:
            logger.info("✅ ДАННЫЕ ПОЛУЧЕНЫ!")
            found = parse(data)
            if found:
                await bot.send_message(CHANNEL_ID, "\n\n".join(found))
        else:
            logger.info("⏳ Прокси не ответил, жду...")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
