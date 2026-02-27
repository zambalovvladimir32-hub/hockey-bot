import asyncio
import os
import logging
import sys
from aiogram import Bot
import aiohttp
from aiohttp_socks import ProxyConnector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Берем всё из переменных Railway
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL")

bot = Bot(token=TOKEN)
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    # Настраиваем подключение через прокси (поддерживает и http, и socks5)
    connector = ProxyConnector.from_url(PROXY_URL) if PROXY_URL else None
    
    headers = {
        "x-fsign": "SW9D1eZo",
        "Origin": "https://www.flashscore.ru",
        "Referer": "https://www.flashscore.ru/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(URL, headers=headers, timeout=20) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if len(text) > 500:
                        return text
                logger.warning(f"⚠️ Статус: {resp.status}, Размер: {resp.content_length}")
    except Exception as e:
        logger.error(f"🔥 Ошибка сети/прокси: {e}")
    return None

def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    for block in blocks[1:]:
        # Ищем маркеры 2-го периода в кодах Flashscore
        if any(x in block for x in ['TT÷2', 'NS÷2']):
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                matches.append(f"🏒 **{home} — {away}**\n⏱ Идет 2-й период")
            except:
                continue
    return matches

async def main():
    logger.info(f"🚀 СТАРТ. Прокси используется: {'ДА' if PROXY_URL else 'НЕТ'}")
    
    while True:
        raw_data = await get_data()
        if raw_data:
            logger.info("✅ ДАННЫЕ УСПЕШНО ПОЛУЧЕНЫ")
            found = parse(raw_data)
            if found:
                await bot.send_message(CHANNEL_ID, "\n\n".join(found[:10]), parse_mode="Markdown")
                logger.info(f"📡 Отправлено матчей: {len(found)}")
            else:
                logger.info("🔎 Матчей во 2-м периоде пока нет.")
        else:
            logger.info("⏳ Попытка через 2 минуты...")
        
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
