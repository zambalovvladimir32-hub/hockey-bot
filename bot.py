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

# Используем мобильный фид агрегатора, который обычно открыт для зарубежных IP
URL = "https://data.livescore.bz/api/hockey/live" 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json"
}

async def check_hockey_free():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            logger.info("--- ПРОВЕРКА ЧЕРЕЗ ОТКРЫТЫЙ ХОККЕЙНЫЙ ФИД ---")
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка доступа: {resp.status}. Пробую резервный путь...")
                    return

                data = await resp.json()
                # Обычно структура: { "games": [...] }
                games = data.get('games', [])
                
                found = 0
                for g in games:
                    found += 1
                    t1 = g.get('home_team', '???')
                    t2 = g.get('away_team', '???')
                    score = f"{g.get('home_score', 0)}:{g.get('away_score', 0)}"
                    period = str(g.get('period', '')) 
                    
                    logger.info(f"ВИЖУ: {t1} {score} {t2} (Период: {period})")

                    # Если 2-й период (обычно обозначается как '2', '2nd' или 'P2')
                    if "2" in period:
                        msg = f"🏒 **БЕСПЛАТНЫЙ СИГНАЛ: 2-й ПЕРИОД**\n📊 {t1} {score} {t2}\n📢 Статус: {period}"
                        await bot.send_message(CHANNEL_ID, msg)

                if found == 0:
                    logger.info("В бесплатном фиде сейчас нет активных игр.")

        except Exception as e:
            logger.error(f"Ошибка парсера: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🛰 Поиск через открытый фид запущен...")
    while True:
        await check_hockey_free()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
