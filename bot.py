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

# Новый источник - прямой фид Flashscore (через прокси-шлюз)
URL = "https://d.flashscore.com/x/feed/f_4_0_2_ru-ru_1" 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Referer": "https://www.flashscore.ru/",
    "X-Requested-With": "XMLHttpRequest"
}

async def check_flashscore():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            logger.info("--- СКАНИРОВАНИЕ FLASHSCORE (ВХЛ) ---")
            async with session.get(URL, timeout=15) as resp:
                text = await resp.text()
                
                # Flashscore отдает данные в текстовом формате, разделенном тильдами ~
                # Ищем матчи Норильска или Югры
                if "Norilsk" in text or "Yugra" in text or "Норильск" in text:
                    logger.info("🎯 ЕСТЬ КОНТАКТ! Вижу Норильск в линии.")
                    
                    # Для теста: если нашли хоть какое-то упоминание, шлем сигнал
                    msg = "🏒 **ОБНАРУЖЕН МАТЧ ВХЛ**\n🏔 ХК Норильск — Югра\n✅ Бот видит игру через Flashscore!"
                    await bot.send_message(CHANNEL_ID, msg)
                else:
                    logger.warning("Норильск всё еще не найден в этом фиде. Проверяю альтернативы...")
                    
        except Exception as e:
            logger.error(f"Ошибка Flashscore: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🔄 Переключение на Flashscore-фид для ВХЛ...")
    while True:
        await check_flashscore()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
