import asyncio
import aiohttp
import os
import logging
import sys
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Ультимативный API эндпоинт (JSON формат)
URL = "https://m.flashscore.ru/x/api/v1/live-matches/hockey"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json"
}

async def ultimate_check():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            logger.info("--- УЛЬТИМАТИВНЫЙ ПОИСК (JSON API) ---")
            async with session.get(URL, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    matches = data.get('data', [])
                    found_vhl = False
                    
                    for match in matches:
                        t1 = match.get('home_name', '')
                        t2 = match.get('away_name', '')
                        score = f"{match.get('home_score', '0')}:{match.get('away_score', '0')}"
                        status = match.get('status_type', '') # Период
                        
                        logger.info(f"ВИЖУ: {t1} {score} {t2} (Статус: {status})")
                        
                        if "Norilsk" in t1 or "Yugra" in t2 or "Норильск" in t1:
                            found_vhl = True
                            msg = f"🎯 **МАТЧ НАЙДЕН!**\n🏔 {t1} {score} {t2}\n⏱ Статус: {status}\n⚡️ Связь установлена!"
                            await bot.send_message(CHANNEL_ID, msg)
                    
                    if not found_vhl:
                        logger.warning("Норильск отсутствует в JSON-фиде. В линии только зарубежные лиги?")
                else:
                    logger.error(f"Ошибка API: {resp.status}")
                    
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🚀 Запуск ультимативного поиска ВХЛ...")
    while True:
        await ultimate_check()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
