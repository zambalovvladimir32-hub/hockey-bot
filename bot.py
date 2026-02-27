import asyncio
import os
import logging
import sys
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY = os.getenv("PROXY_URL")

bot = Bot(token=TOKEN)
# Хоккейный фид (прямой адрес)
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    headers = {
        "x-fsign": "SW9D1eZo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://www.flashscore.ru",
        "Referer": "https://www.flashscore.ru/",
    }
    
    proxies = {"http": PROXY, "https": PROXY} if PROXY else None

    try:
        # impersonate="chrome110" делает запрос не отличимым от браузера
        async with AsyncSession(impersonate="chrome110") as s:
            logger.info(f"📡 Запрос через Webshare...")
            r = await s.get(URL, headers=headers, proxies=proxies, timeout=30)
            
            if r.status_code == 200:
                if len(r.text) > 1000:
                    return r.text
                else:
                    logger.warning(f"⚠️ Сайт прислал пустой ответ ({len(r.text)} байт).")
            else:
                logger.error(f"❌ Ошибка сервера: {r.status_code}")
    except Exception as e:
        logger.error(f"🔥 Ошибка Webshare/Railway: {e}")
    return None

def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    for block in blocks[1:]:
        # Метки 2-го периода в коде Flashscore
        if 'TT÷2' in block or 'NS÷2' in block:
            try:
                # AE - Домашняя команда, AF - Гости
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                matches.append(f"🏒 **{home} — {away}**\n⏱ Идет 2-й период")
            except:
                continue
    return matches

async def main():
    logger.info("🚀 БОТ ЗАПУЩЕН НА PROXY WEBSHARE")
    
    while True:
        raw_data = await get_data()
        if raw_data:
            logger.info(f"✅ ДАННЫЕ ПОЛУЧЕНЫ! ({len(raw_data)} байт)")
            found = parse(raw_data)
            if found:
                report = "🥅 **LIVE: ХОККЕЙ (2-Й ПЕРИОД)**\n\n" + "\n\n".join(found[:10])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info(f"📡 Сигналы ушли в канал: {len(found)}")
            else:
                logger.info("🔎 2-й период в матчах пока не начался.")
        else:
            logger.info("⏳ Ожидание (2 мин)...")
        
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
