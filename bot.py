import asyncio
import os
import logging
import sys
from aiogram import Bot
import aiohttp

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Данные только из переменных!
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY = os.getenv("PROXY_URL")

bot = Bot(token=TOKEN)
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    headers = {
        "x-fsign": "SW9D1eZo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://www.flashscore.ru",
        "Referer": "https://www.flashscore.ru/"
    }
    
    # Пытаемся подключиться (с прокси или без)
    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"🛰 Запрос через: {PROXY if PROXY else 'прямое соединение'}")
            async with session.get(URL, headers=headers, proxy=PROXY, timeout=15) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if len(text) > 500:
                        return text
                logger.warning(f"⚠️ Ответ сайта: {resp.status}")
    except Exception as e:
        logger.error(f"❌ Ошибка соединения: {e}")
    return None

def parse(data):
    matches = []
    # Быстрый срез данных по хоккейным кодам
    for block in data.split('~AA÷')[1:]:
        if any(x in block for x in ['TT÷2', 'NS÷2', 'П2']):
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                matches.append(f"🏒 **{home} — {away}**\n⏱ Идет 2-й период!")
            except: continue
    return matches

async def main():
    logger.info("🚀 БОТ ОЖИЛ И ГОТОВ К РАБОТЕ")
    while True:
        raw = await get_data()
        if raw:
            logger.info(f"✅ УСПЕХ! Получено {len(raw)} байт данных.")
            found = parse(raw)
            if found:
                await bot.send_message(CHANNEL_ID, "\n\n".join(found[:10]), parse_mode="Markdown")
                logger.info(f"📡 Сигналы ушли в Telegram: {len(found)}")
        else:
            logger.info("⏳ Данных нет, следующая попытка через минуту...")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
