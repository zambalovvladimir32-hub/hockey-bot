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

# Прямой фид всех активных игр (включая ВХЛ)
URL = "https://d.flashscore.com/x/feed/f_4_0_2_ru-ru_1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "X-Referer": "https://www.flashscore.ru/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "*/*"
}

async def check_vhl():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            logger.info("--- ГЛУБОКОЕ СКАНИРОВАНИЕ ЛИНИИ ---")
            async with session.get(URL, timeout=20) as resp:
                raw_data = await resp.text()
                
                # Проверяем наличие матча по частям названий
                targets = ["Norilsk", "Yugra", "Норильск", "Югра"]
                found = any(target in raw_data for target in targets)
                
                if found:
                    logger.info("🎯 НОРИЛЬСК ОБНАРУЖЕН В СЫРЫХ ДАННЫХ!")
                    # Вырезаем кусок текста вокруг названия для отладки в логи
                    start_idx = raw_data.find("Norilsk") if "Norilsk" in raw_data else raw_data.find("Норильск")
                    logger.info(f"Данные матча: {raw_data[start_idx:start_idx+100]}")
                    
                    await bot.send_message(CHANNEL_ID, "✅ **Матч найден!**\n🏔 ХК Норильск — Югра обнаружен в системе Flashscore.\n📡 Начинаю слежение за периодами.")
                else:
                    logger.warning("Матч пока не прогрузился в общий фид. Пробую расширенный поиск...")
                    # Попробуем альтернативный ID фида, если первый пуст
                    alt_url = "https://d.flashscore.com/x/feed/f_4_1_2_ru-ru_1"
                    async with session.get(alt_url, timeout=15) as alt_resp:
                        alt_text = await alt_resp.text()
                        if any(t in alt_text for t in targets):
                            logger.info("🎯 НОРИЛЬСК НАЙДЕН ЧЕРЕЗ АЛЬТЕРНАТИВНЫЙ ФИД!")
                            await bot.send_message(CHANNEL_ID, "✅ Матч ВХЛ найден через резервный канал!")

        except Exception as e:
            logger.error(f"Ошибка при поиске ВХЛ: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🕵️‍♂️ Запущен поиск матча Норильск — Югра...")
    while True:
        await check_vhl()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
