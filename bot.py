import asyncio
import aiohttp
import os
import logging
import sys
from aiogram import Bot

# Логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)

# Прямой адрес к потоку данных (заменяем Livescore на альтернативный узел)
URL = "https://d.flashscore.com/x/feed/l_3_1" 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Referer": "https://www.flashscore.com/"
}

sent_signals = set()

async def check_logic():
    logger.info("--- ФИНАЛЬНЫЙ ШТУРМ (FLASHSCORE DATA) ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                raw_data = await resp.text()
                
                # Flashscore отдает данные специфической строкой, ищем матчи
                matches = raw_data.split('~')
                total = 0
                
                for m_str in matches:
                    if 'AA÷' in m_str: # Признак начала данных матча
                        total += 1
                        # Извлекаем команды, счет и время (упрощенно для теста)
                        # Если этот метод сработает и выдаст число > 0, я допишу точный парсер минут
                        
                logger.info(f"ИТОГ: Система Flashscore видит {total} игр.")
                
                # Если он увидел Омск, отправим сигнал
                if total > 0 and "Омские Крылья" in raw_data:
                    await bot.send_message(CHANNEL_ID, "🚀 ЕСТЬ КОНТАКТ! Бот увидел матч Омска.")

        except Exception as e:
            logger.error(f"Ошибка: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🛠 Переход на протокол Flashscore. Проверяю связь...")
    while True:
        await check_logic()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
