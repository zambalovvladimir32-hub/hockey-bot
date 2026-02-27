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

# Ищем через Google Search (этот URL почти невозможно заблокировать)
URL = "https://www.google.com/search?q=хоккей+вхл+норильск+югра+счет+онлайн"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

async def check_via_google():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            logger.info("--- ПРОВЕРКА ЧЕРЕЗ GOOGLE ---")
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Google отклонил запрос: {resp.status}")
                    return

                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Ищем любые упоминания счета или команд на странице
                page_text = soup.get_text()
                
                if "Норильск" in page_text or "Norilsk" in page_text:
                    logger.info("🎯 GOOGLE ПОДТВЕРДИЛ: Матч есть в выдаче!")
                    
                    # Попробуем найти цифры счета (упрощенно)
                    # В реальном лайве Google выводит их в специальных классах, 
                    # но даже просто найти упоминание - это уже победа связи.
                    
                    await bot.send_message(CHANNEL_ID, "✅ **Матч найден через Google!**\n🏔 ХК Норильск — Югра\n📡 Связь установлена через поисковую выдачу.")
                else:
                    logger.warning("Google пока не вывел плашку лайва. Ждем...")

        except Exception as e:
            logger.error(f"Ошибка Google-парсера: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🌐 Запускаю обход блокировок через Google...")
    while True:
        await check_via_google()
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
