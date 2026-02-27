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

# Пробуем достучаться через альтернативный прокси-узел или зеркало
URLS = [
    "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0",
    "http://1.1.1.1/api/live" # Заглушка для теста IP
]

async def check_logic():
    logger.info("--- ФИНАЛЬНЫЙ ТЕСТ СВЯЗИ (DNS BYPASS) ---")
    
    # Пытаемся понять, видит ли сервер вообще интернет
    async with aiohttp.ClientSession() as session:
        try:
            # Проверка через Google (его точно не должны блокировать)
            async with session.get("https://www.google.com", timeout=5) as r:
                logger.info(f"Связь с Google: {r.status} (Интернет есть)")
        except Exception as e:
            logger.error(f"ПОЛНАЯ ИЗОЛЯЦИЯ: Сервер не видит даже Google. Ошибка: {e}")

        try:
            # Пытаемся пробиться к Livescore через его прямой IP, если DNS тупит
            # (Используем заголовки, чтобы не забанили)
            headers = {"User-Agent": "Mozilla/5.0", "Host": "prod-public-api.livescore.com"}
            async with session.get(URLS[0], headers=headers, timeout=15) as resp:
                data = await resp.json()
                total = 0
                for stage in data.get('Stages', []):
                    for event in stage.get('Events', []):
                        total += 1
                
                logger.info(f"ПРОРЫВ! Найдено матчей: {total}")
                if total > 0:
                    await bot.send_message(CHANNEL_ID, f"🚀 Связь установлена! Вижу {total} матчей.")

        except Exception as e:
            logger.error(f"Не удалось пробить блокировку: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🔎 Запускаю глубокую диагностику сети...")
    while True:
        await check_logic()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
