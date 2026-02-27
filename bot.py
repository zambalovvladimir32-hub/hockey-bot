import asyncio
import aiohttp
import os
import logging
import sys
from aiogram import Bot

# Настройка логирования для Amvera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)

# Поток данных от российского Чемпионата (Hockey Live)
URL = "https://www.championat.com/stat/live/hockey/" 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8"
}

sent_signals = set()

async def check_logic():
    logger.info("--- ПРОВЕРКА ЧЕРЕЗ CHAMPIONAT (РФ) ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=20) as resp:
                if resp.status != 200:
                    logger.error(f"Чемпионат недоступен: {resp.status}")
                    return
                
                html = await resp.text()
                
                # Ищем матчи в HTML (упрощенный поиск по названиям команд)
                total = html.count('status="live"') # Считаем живые матчи в разметке
                
                # Поиск конкретно Омска для теста
                is_omsk_live = "Омские Крылья" in html
                
                logger.info(f"ИТОГ: Найдено матчей в статусе LIVE: {total}")
                
                if is_omsk_live:
                    logger.info("🎯 ОМСК НАЙДЕН В СЕТИ!")
                    if "omsk_found" not in sent_signals:
                        await bot.send_message(CHANNEL_ID, "🏒 **СВЯЗЬ УСТАНОВЛЕНА!**\nВижу матч: Омские Крылья — Динамо СПб\nИсточник: Чемпионат.com")
                        sent_signals.add("omsk_found")

        except Exception as e:
            logger.error(f"Ошибка парсинга Чемпионата: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🇷🇺 Бот переведен на российские серверы (Championat). Ищу Омск...")
    while True:
        await check_logic()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
