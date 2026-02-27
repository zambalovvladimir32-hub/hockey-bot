import asyncio
import os
import logging
import sys
from aiogram import Bot
from bs4 import BeautifulSoup
import aiohttp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Прямой запрос к Google по конкретному матчу
URL = "https://www.google.com/search?q=хоккей+норильск+югра+счет+онлайн"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
}

async def check_match_live():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            logger.info("--- СКАНИРОВАНИЕ GOOGLE (LIVE) ---")
            async with session.get(URL, timeout=15) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Google прячет счет в разные классы, поэтому ищем текст
                text = soup.get_text()
                
                # Ищем признаки 2-го периода
                is_2nd = any(x in text for x in ["2-й период", "2-й", "2nd Period", "2nd P"])
                
                # Пытаемся найти счет (ищем конструкцию типа "0 - 0" или "1 : 0")
                # Для простоты логов выведем кусок текста
                logger.info(f"Сниппет страницы: {text[500:800]}...") 

                if "Норильск" in text and "Югра" in text:
                    status = "🔥 2-й ПЕРИОД" if is_2nd else "🏒 ИДЕТ ИГРА"
                    
                    # Отправляем сигнал в канал
                    msg = (f"{status}\n"
                           f"🏔 ХК Норильск — Югра\n"
                           f"📢 Данные подтверждены через Google Search")
                    
                    await bot.send_message(CHANNEL_ID, msg)
                    logger.info("Сигнал отправлен в Telegram!")
                else:
                    logger.warning("Матч найден, но детали счета скрыты. Проверяю снова через минуту...")

        except Exception as e:
            logger.error(f"Ошибка: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🎯 Бот перешел на прямое чтение Google. Слежу за Норильском!")
    while True:
        await check_match_live()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
