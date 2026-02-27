import asyncio
import os
import logging
import sys
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)
# Ссылка на фид (проверенная)
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    headers = {
        "x-fsign": "SW9D1eZo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.flashscore.ru",
        "Referer": "https://www.flashscore.ru/",
    }
    
    try:
        # impersonate="chrome110" делает запрос идентичным реальному браузеру
        async with AsyncSession(impersonate="chrome110") as s:
            r = await s.get(URL, headers=headers, timeout=20)
            if r.status_code == 200:
                # Если данных больше 500 символов - это успех
                if len(r.text) > 500:
                    return r.text
                else:
                    logger.warning(f"⚠️ Мало данных: {len(r.text)} байт. Похоже на заглушку.")
            else:
                logger.error(f"❌ Ошибка сайта: {r.status_code}")
    except Exception as e:
        logger.error(f"🔥 Критическая ошибка: {e}")
    return None

def parse(data):
    matches = []
    # Маркеры начала матча в API Flashscore
    blocks = data.split('~AA÷')
    for block in blocks[1:]:
        # Ищем 2-й период (TT=2)
        if 'TT÷2' in block or 'NS÷2' in block:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                matches.append(f"🏒 **{home} — {away}**\n⏱ Идет 2-й период")
            except:
                continue
    return matches

async def main():
    logger.info("🚀 БОТ ЗАПУЩЕН С ИМИТАЦИЕЙ БРАУЗЕРА")
    while True:
        raw_data = await get_data()
        if raw_data:
            logger.info(f"✅ ДАННЫЕ ПОЛУЧЕНЫ ({len(raw_data)} байт)")
            found = parse(raw_data)
            if found:
                report = "🥅 **LIVE: 2-Й ПЕРИОД**\n\n" + "\n\n".join(found[:10])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info(f"📡 Сигналы отправлены!")
            else:
                logger.info("🔎 Матчей во 2-м периоде пока нет.")
        else:
            logger.info("⏳ Ждем следующего окна...")
        
        # Проверяем каждые 2 минуты
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
