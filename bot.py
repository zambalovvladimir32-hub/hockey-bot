import asyncio
import os
import logging
import sys
import random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
# Берем прокси и убираем лишние пробелы
PROXY_URL = os.getenv("PROXY_URL", "").strip()

bot = Bot(token=TOKEN)

URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"
FSIGN = "SW9D1eZo"

async def get_data():
    headers = {
        "x-fsign": FSIGN,
        "Origin": "https://www.flashscore.ru",
        "Referer": "https://www.flashscore.ru/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    # Прямая передача прокси в сессию
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    
    async with AsyncSession(impersonate="chrome120") as session:
        try:
            # Большая пауза, чтобы прокси проснулся
            await asyncio.sleep(random.uniform(5, 10))
            
            resp = await session.get(URL, headers=headers, proxies=proxies, timeout=40)
            
            if resp.status_code == 200 and len(resp.text) > 500:
                return resp.text
            
            logger.warning(f"⚠️ Статус: {resp.status_code}, Размер: {len(resp.text) if resp.text else 0}")
            return None
        except Exception as e:
            logger.error(f"🔥 Ошибка: {e}")
            return None

def parse(raw):
    matches = []
    blocks = raw.split('~AA÷')
    for block in blocks[1:]:
        if 'AE÷' not in block: continue
        # Ищем 2-й период (метки TT÷2 или П2)
        if any(x in block for x in ['TT÷2', 'NS÷2', 'П2']):
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                s1 = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                s2 = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                matches.append(f"🏒 **{home} {s1}:{s2} {away}**\n⏱ Идет 2-й период")
            except: continue
    return matches

async def main():
    logger.info(f"🚀 СТАРТ С ПРОКСИ: {PROXY_URL[:15]}...")
    
    while True:
        data = await get_data()
        if data:
            logger.info(f"✅ ДАННЫЕ ПОЛУЧЕНЫ! ({len(data)} байт)")
            found = parse(data)
            if found:
                text = "🥅 **LIVE: 2-Й ПЕРИОД**\n\n" + "\n\n".join(found[:10])
                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                logger.info(f"📡 Сигналы отправлены: {len(found)}")
            else:
                logger.info("🔎 Матчей во 2-м периоде пока нет.")
        else:
            logger.info("⏳ Не удалось зайти. Повтор через 2 минуты...")
        
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
