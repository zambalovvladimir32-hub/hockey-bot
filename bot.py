import asyncio
import os
import logging
import sys
import re
from aiogram import Bot
from bs4 import BeautifulSoup
import aiohttp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Поисковый запрос, который выводит плашку счета
URL = "https://www.google.com/search?q=норильск+югра+хоккей+счет+онлайн"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9"
}

async def scout_google():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            logger.info("--- РЕНТГЕН GOOGLE-ВЫДАЧИ ---")
            async with session.get(URL, timeout=15) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Чистим текст от мусора
                raw_text = soup.get_text(separator=' ').lower()
                
                # 1. Проверяем, что мы вообще на нужной странице
                if "норильск" in raw_text and "югра" in raw_text:
                    logger.info("🎯 Команды в выдаче подтверждены.")
                    
                    # 2. Ищем упоминание 2-го периода (разные варианты написания)
                    is_2nd = any(p in raw_text for p in ["2-й период", "2-й", "2nd period", "второй период"])
                    
                    # 3. Пытаемся вытянуть счет через регулярные выражения (ищем цифра-дефис-цифра)
                    score_match = re.search(r'(\d)\s*[:\-]\s*(\d)', raw_text)
                    current_score = score_match.group(0) if score_match else "0:0 (или не найден)"

                    if is_2nd:
                        msg = (f"🔥 **ЕСТЬ СИГНАЛ: 2-й ПЕРИОД**\n"
                               f"🏒 Норильск vs Югра\n"
                               f"📊 Текущий счет по Google: {current_score}\n"
                               f"🌐 Источник: Поисковая выдача")
                        await bot.send_message(CHANNEL_ID, msg)
                        logger.info("✅ Сигнал отправлен!")
                    else:
                        logger.info(f"Матч идет, но 2-й период еще не начался (или уже прошел). Счет: {current_score}")
                else:
                    logger.warning("Google обновил выдачу, команды временно пропали. Ждем...")

        except Exception as e:
            logger.error(f"Ошибка сканера: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🚀 Система слежения за ВХЛ активирована через Google-фильтр.")
    while True:
        await scout_google()
        # Проверяем раз в 45 секунд, чтобы Google не забанил за частые запросы
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
