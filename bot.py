import asyncio
import os
import logging
import sys
from aiogram import Bot
import aiohttp

# Настройка логов для Railway
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
# Важно: чистим строку от лишних символов
PROXY = os.getenv("PROXY_URL", "").strip()

bot = Bot(token=TOKEN)
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    headers = {
        "x-fsign": "SW9D1eZo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    # Если прокси пустой или кривой, попробуем без него
    current_proxy = PROXY if PROXY.startswith("http") else None
    
    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"🛰 Запрос. Прокси: {current_proxy if current_proxy else 'НЕТ'}")
            async with session.get(URL, headers=headers, proxy=current_proxy, timeout=20) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if len(text) > 200:
                        return text
                logger.warning(f"⚠️ Ответ сайта: {resp.status}")
    except Exception as e:
        logger.error(f"❌ Ошибка сети: {e}")
    return None

def parse(data):
    matches = []
    # Делим по маркерам матчей Flashscore
    blocks = data.split('~AA÷')
    for block in blocks[1:]:
        # Проверяем, идет ли 2-й период (коды TT÷2 или NS÷2)
        if 'TT÷2' in block or 'NS÷2' in block:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                matches.append(f"🏒 **{home} — {away}**\n⏱ Идет 2-й период")
            except:
                continue
    return matches

async def main():
    logger.info("🔥 БОТ СТАРТОВАЛ С ЧИСТОГО ЛИСТА")
    while True:
        raw_data = await get_data()
        if raw_data:
            logger.info(f"✅ УСПЕХ! Получено данных: {len(raw_data)} байт")
            found = parse(raw_data)
            if found:
                # Отправляем максимум 5 матчей, чтобы не спамить
                report = "🥅 **LIVE: 2-Й ПЕРИОД**\n\n" + "\n\n".join(found[:5])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info(f"📡 Отправлено в канал: {len(found)} матчей")
            else:
                logger.info("🔎 Матчей во 2-м периоде сейчас нет.")
        else:
            logger.info("⏳ Данные не получены. Жду 2 минуты...")
        
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
