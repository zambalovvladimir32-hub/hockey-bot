import asyncio
import os
import logging
from aiogram import Bot
import aiohttp
from aiohttp_socks import ProxyConnector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
# Чистим строку прокси от мусора
PROXY_URL = os.getenv("PROXY_URL", "").strip()

bot = Bot(token=TOKEN)
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def fetch():
    # Настраиваем коннектор через прокси
    connector = ProxyConnector.from_url(PROXY_URL) if PROXY_URL else None
    
    headers = {
        "x-fsign": "SW9D1eZo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://www.flashscore.ru",
        "Referer": "https://www.flashscore.ru/"
    }

    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(URL, headers=headers, timeout=20) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if len(text) > 500:
                        return text
                logger.warning(f"⚠️ Статус: {resp.status}, Размер: {resp.content_length}")
                return None
    except Exception as e:
        logger.error(f"🔥 Ошибка: {e}")
        return None

def parse(raw):
    matches = []
    for block in raw.split('~AA÷')[1:]:
        if 'AE÷' not in block: continue
        # Проверка на 2-й период (TT=2 или П2)
        if any(x in block for x in ['TT÷2', 'NS÷2', 'П2', '2-Й ПЕРИОД']):
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                s1 = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                s2 = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                matches.append(f"🏒 **{home} {s1}:{s2} {away}**")
            except: continue
    return matches

async def main():
    logger.info(f"🚀 СТАРТ. Прокси: {PROXY_URL[:15]}...")
    while True:
        data = await fetch()
        if data:
            logger.info(f"✅ УСПЕХ! Данные получены.")
            results = parse(data)
            if results:
                await bot.send_message(CHANNEL_ID, "🥅 **LIVE: 2-Й ПЕРИОД**\n\n" + "\n\n".join(results[:10]), parse_mode="Markdown")
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
