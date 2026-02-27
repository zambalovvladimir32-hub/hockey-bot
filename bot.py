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

# Пробуем альтернативный легкий фид
URL = "https://core-sport.rambler.ru/v1/export/free/livescore?project=sport&category=hockey"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://sport.rambler.ru",
    "Referer": "https://sport.rambler.ru/"
}

async def check_hockey():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            logger.info("--- ПРОВЕРКА ЧЕРЕЗ RAMBLER-SPORT (ВХЛ/КХЛ) ---")
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Сервер послал нас: {resp.status}")
                    return

                data = await resp.json()
                # Рамблер обычно отдает ВХЛ без проблем
                matches = data.get('matches', [])
                
                found = 0
                for m in matches:
                    found += 1
                    t1 = m.get('home_team', {}).get('name', '???')
                    t2 = m.get('away_team', {}).get('name', '???')
                    score = f"{m.get('home_score', 0)}:{m.get('away_score', 0)}"
                    status = str(m.get('status', '')) # Ищем 2-й период
                    
                    logger.info(f"ВИЖУ: {t1} {score} {t2} (Период: {status})")

                    # Если в статусе есть цифра 2 или слово '2-й'
                    if "2" in status or "2nd" in status.lower():
                        msg = f"🏒 **СТРАТЕГИЯ: 2-й ПЕРИОД**\n📊 {t1} {score} {t2}\n✅ Источник: Rambler"
                        await bot.send_message(CHANNEL_ID, msg)

                if found == 0:
                    logger.info("Матчей в лайве пока нет.")

        except Exception as e:
            logger.error(f"Ошибка парсера: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🛠 Запущен бесплатный 'Партизан' (ВХЛ/КХЛ)...")
    while True:
        await check_hockey()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
