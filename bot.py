import asyncio
import os
import logging
import sys
from aiogram import Bot
import aiohttp
from aiohttp_socks import ProxyConnector

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL", "").strip()

bot = Bot(token=TOKEN)

async def check_ip(connector):
    """Проверка, через какой IP мы реально выходим в сеть"""
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get("https://api.ipify.org", timeout=10) as resp:
                ip = await resp.text()
                logger.info(f"🌐 Текущий IP выхода: {ip}")
                return ip
    except Exception as e:
        logger.error(f"❌ Не удалось проверить IP: {e}")
        return None

async def main():
    logger.info("🚀 ЗАПУСК ПРОВЕРКИ...")
    
    # Пытаемся подключиться
    connector = ProxyConnector.from_url(PROXY_URL) if PROXY_URL else None
    
    # Сначала проверяем, работает ли прокси вообще
    current_ip = await check_ip(connector)
    
    if current_ip and "74.122.59.102" in current_ip:
        logger.info("✅ ПРОКСИ РАБОТАЕТ! Начинаю парсинг...")
    else:
        logger.error("🚨 ПРОКСИ НЕ ПРИМЕНИЛСЯ или ОШИБКА АВТОРИЗАЦИИ.")
        if not PROXY_URL:
            logger.error("Переменная PROXY_URL пуста!")

    # Твой основной цикл здесь...
    # (Добавь сюда логику get_data и parse из предыдущего шага)

if __name__ == "__main__":
    asyncio.run(main())
