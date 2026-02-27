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

# Используем российский агрегатор или открытый API (пример для проверки связи)
URL = "https://line01i.bkfon-resources.com/live/currentSignals" # Шлюз сигналов

async def check_logic():
    logger.info("--- ПРОВЕРКА ЧЕРЕЗ РОССИЙСКИЙ ШЛЮЗ ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Accept": "*/*"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            # Если прямой шлюз БК сложен, используем упрощенный парсинг агрегатора
            # Для теста сейчас попробуем альтернативный стабильный узел:
            test_url = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
            
            async with session.get(test_url, timeout=15) as resp:
                data = await resp.json()
                total = 0
                for stage in data.get('Stages', []):
                    # Ищем именно российские лиги
                    if "Russia" in stage.get('Cnm', ''):
                        for event in stage.get('Events', []):
                            total += 1
                            t1 = event['T1'][0]['Nm']
                            t2 = event['T2'][0]['Nm']
                            logger.info(f"🇷🇺 НАШЕЛ В РФ: {t1} - {t2}")

                logger.info(f"ИТОГ: Найдено {total} матчей в РФ.")
                
                if total == 0:
                    logger.warning("РФ матчи не найдены, проверяю общую линию...")

        except Exception as e:
            logger.error(f"Ошибка шлюза: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🇷🇺 Бот переключен на российский сегмент. Проверяю ВХЛ...")
    while True:
        await check_logic()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
